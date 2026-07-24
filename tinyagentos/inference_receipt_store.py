from __future__ import annotations

"""Inference receipt store - Bean-1 of the silicon-bean integration.

Append-only, hash-only ledger of every model inference an agent makes,
written at the LiteLLM choke point (see
docs/design/silicon-bean-integration.md).  One sqlbook per agent at
``data/agent-memory/{agent_slug}/receipts.sqlbook``; the caller supplies
the full path.

The file follows the sqlbook shape for the (draft) planekey
``inference-receipts`` profile: a one-row ``book`` table identifying the
artifact, plus the ``inference`` table itself.  The store NEVER receives
prompt or response text - only sha256 hex digests computed by the caller
(manifest mode: hashes + metadata, no content retention).

Like receipt_store.py (the ACTION-receipt plane), this is append-only:
there is deliberately no public update or delete method.  A receipt, once
written, is immutable history.  ``signature`` stays NULL in Bean-1; agent-
held Ed25519 signing lands in Bean-2+ (the column exists so the schema
matches the profile).
"""

import logging
import secrets
from datetime import datetime, timezone
from typing import Callable

import aiosqlite

from tinyagentos.base_store import BaseStore

logger = logging.getLogger(__name__)

_ALPHABET = "abcdefghijklmnopqrstuvwxyz234567"

BOOK_PROFILE = "inference-receipts"
BOOK_VERSION = "0.1"

SCHEMA = """
CREATE TABLE IF NOT EXISTS book (
    title      TEXT,
    version    TEXT,
    profile    TEXT DEFAULT 'inference-receipts',
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS inference (
    inference_id      TEXT PRIMARY KEY,
    trace_id          TEXT,
    model_id          TEXT NOT NULL,
    prompt_hash       TEXT NOT NULL,
    output_hash       TEXT NOT NULL,
    prompt_tokens     INTEGER,
    completion_tokens INTEGER,
    started_at        TEXT,
    completed_at      TEXT,
    status            TEXT DEFAULT 'success',
    signature         TEXT
);
"""

_COLS = (
    "inference_id, trace_id, model_id, prompt_hash, output_hash, "
    "prompt_tokens, completion_tokens, started_at, completed_at, status, signature"
)


def _new_id() -> str:
    return "inf-" + "".join(secrets.choice(_ALPHABET) for _ in range(8))


def _row_to_receipt(row: aiosqlite.Row) -> dict:
    return {
        "inference_id": row["inference_id"],
        "trace_id": row["trace_id"],
        "model_id": row["model_id"],
        "prompt_hash": row["prompt_hash"],
        "output_hash": row["output_hash"],
        "prompt_tokens": row["prompt_tokens"],
        "completion_tokens": row["completion_tokens"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
        "status": row["status"],
        "signature": row["signature"],
    }


class InferenceReceiptStore(BaseStore):
    """Append-only per-agent store of Bean-1 hash-only inference receipts.

    No public update or delete: rows are immutable once written.  Returned
    newest-first by insertion order (SQLite rowid) so history is stable even
    when two receipts share a timestamp.
    """

    SCHEMA = SCHEMA

    async def init(self) -> None:
        await super().init()
        if self._db is not None:
            self._db.row_factory = aiosqlite.Row

    async def _post_init(self) -> None:
        """Seed the one-row ``book`` table on first open (sqlbook identity)."""
        async with self._db.execute("SELECT COUNT(*) FROM book") as cur:
            (count,) = await cur.fetchone()
        if count == 0:
            await self._db.execute(
                "INSERT INTO book (title, version, profile, created_at) VALUES (?, ?, ?, ?)",
                (
                    f"inference receipts: {self.db_path.parent.name}",
                    BOOK_VERSION,
                    BOOK_PROFILE,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            await self._db.commit()

    async def book(self) -> dict | None:
        """Return the sqlbook identity row, or ``None`` (never after init)."""
        if self._db is None:
            raise RuntimeError("InferenceReceiptStore not initialised - call init() first")
        async with self._db.execute(
            "SELECT title, version, profile, created_at FROM book LIMIT 1"
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        return {
            "title": row["title"],
            "version": row["version"],
            "profile": row["profile"],
            "created_at": row["created_at"],
        }

    async def record(
        self,
        *,
        model_id: str,
        prompt_hash: str,
        output_hash: str,
        trace_id: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
        status: str = "success",
        signature: str | None = None,
        signer: "Callable[[dict], str] | None" = None,
    ) -> str:
        """Append a receipt row and return its generated inference_id.

        ``prompt_hash`` / ``output_hash`` are sha256 hex digests computed by
        the caller - this store never sees message or response text.

        Signing (Bean-2+) is optional and can arrive two ways:

        * ``signature`` — a hex Ed25519 signature the caller already computed.
        * ``signer`` — a callback ``fn(receipt: dict) -> hex``. Because the
          signature must cover the generated ``inference_id`` (which the
          caller cannot know in advance), the store builds the full receipt
          dict here, calls ``signer`` on it, and writes both in one
          append-only insert. Fail-open: if signing raises, the row is still
          written **unsigned** (a receipt must never be lost because signing
          failed) - it verifies as "unsigned", not "invalid".

        Omit both and the column stays NULL exactly as in Bean-1. This store
        never signs on its own; ``signer`` is supplied by the caller (the
        receipt POST route wires in the per-agent key via ``bean_keystore``).
        """
        if self._db is None:
            raise RuntimeError("InferenceReceiptStore not initialised - call init() first")
        if not model_id:
            raise ValueError("model_id is required")
        if not prompt_hash or not output_hash:
            raise ValueError("prompt_hash and output_hash are required")
        inference_id = _new_id()
        if signature is None and signer is not None:
            receipt = {
                "inference_id": inference_id, "trace_id": trace_id,
                "model_id": model_id, "prompt_hash": prompt_hash,
                "output_hash": output_hash, "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens, "started_at": started_at,
                "completed_at": completed_at, "status": status,
            }
            try:
                signature = signer(receipt)
            except Exception as exc:  # fail-open: store unsigned, never drop
                logger.warning("inference_receipt_store: signing failed, storing unsigned: %s", exc)
                signature = None
        await self._db.execute(
            f"INSERT INTO inference ({_COLS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                inference_id, trace_id, model_id, prompt_hash, output_hash,
                prompt_tokens, completion_tokens, started_at, completed_at, status,
                signature,
            ),
        )
        await self._db.commit()
        return inference_id

    async def list(self, limit: int = 50, before: str | None = None) -> list[dict]:
        """Newest-first receipts (insertion order via rowid), bounded.

        ``before`` is an inference_id cursor: only rows inserted before it
        are returned, so callers can page backwards through the ledger.
        An unknown cursor yields an empty page rather than silently
        restarting from the top.
        """
        if self._db is None:
            raise RuntimeError("InferenceReceiptStore not initialised - call init() first")
        limit = max(1, min(int(limit), 1000))
        where, params = "", []
        if before is not None:
            where = " WHERE rowid < (SELECT rowid FROM inference WHERE inference_id = ?)"
            params.append(before)
        async with self._db.execute(
            f"SELECT {_COLS} FROM inference{where} ORDER BY rowid DESC LIMIT ?",
            [*params, limit],
        ) as cur:
            rows = await cur.fetchall()
        return [_row_to_receipt(r) for r in rows]

    async def count(self) -> int:
        """Total number of receipts in the ledger."""
        if self._db is None:
            raise RuntimeError("InferenceReceiptStore not initialised - call init() first")
        async with self._db.execute("SELECT COUNT(*) FROM inference") as cur:
            (count,) = await cur.fetchone()
        return int(count)
