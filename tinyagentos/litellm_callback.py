"""LiteLLM CustomLogger that posts llm_call traces to the taOS trace API.

Registered as a LiteLLM callback so every chat completion routed through
the proxy is automatically captured in the per-agent trace store.

The callback extracts the agent slug from the LiteLLM key alias which the
deployer creates as ``taos-<slug>``. If no alias is found, the event is
recorded under the sentinel slug ``_unknown_`` so it's not silently
dropped.

Authentication uses the local token (``data/.auth_local_token``). The
path is resolved by probing the candidate locations described in
AuthManager.local_token_path(), with a final fallback to the
``TAOS_LOCAL_TOKEN`` env var injected by the deployer.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Sentinel used when no agent slug can be derived from the key alias.
_UNKNOWN_SLUG = "_unknown_"

# Candidate paths for the local auth token, searched in order.
_TOKEN_CANDIDATES = [
    Path("/data/.auth_local_token"),
    Path.home() / ".taos" / ".auth_local_token",
]


def _read_local_token() -> str:
    """Return the local auth token, trying candidate paths then env."""
    env_token = os.environ.get("TAOS_LOCAL_TOKEN", "")
    if env_token:
        return env_token
    for candidate in _TOKEN_CANDIDATES:
        try:
            if candidate.exists():
                return candidate.read_text().strip()
        except OSError:
            pass
    return ""


_budget_store = None
_budget_store_path = None


def _budget_store_for(path: str) -> Any:
    """Lazily open (and cache) the budget store from the env-provided path."""
    global _budget_store, _budget_store_path
    if _budget_store is None or _budget_store_path != path:
        from tinyagentos.agent_budget_store import AgentBudgetStore
        _budget_store = AgentBudgetStore(path)
        _budget_store_path = path
    return _budget_store


def _slug_from_alias(key_alias: str | None) -> str:
    """Extract agent slug from ``taos-<slug>`` key alias."""
    if key_alias and key_alias.startswith("taos-"):
        slug = key_alias[len("taos-"):]
        if slug:
            return slug
    return _UNKNOWN_SLUG


def _prompt_hash(messages: list) -> str:
    """sha256 hex digest of the canonical prompt (Bean-1 inference receipts).

    Canonical form is ``json.dumps`` of the messages list with sorted keys
    and compact separators, so the same conversation always hashes the same
    regardless of dict ordering. ``default=str`` keeps the digest total even
    when a message carries a non-JSON value; the receipt must never be the
    thing that breaks the inference path.
    """
    canonical = json.dumps(
        messages, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _output_hash(text: str) -> str:
    """sha256 hex digest of the response text (empty string hashes too)."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


try:
    from litellm.integrations.custom_logger import CustomLogger as _CustomLogger

    class TaosLiteLLMCallback(_CustomLogger):
        """Posts llm_call + lifecycle/notify on every LiteLLM completion."""

        def __init__(self) -> None:
            super().__init__()
            self._trace_url: str = os.environ.get("TAOS_TRACE_URL", "http://127.0.0.1:6969/api/trace")
            self._notify_url: str = self._trace_url.replace("/api/trace", "/api/lifecycle/notify")
            # Bean-1 inference receipts (hash-only) — same controller, same
            # local-token transport as the trace/notify posts above.
            self._receipts_url_tmpl: str = self._trace_url.replace(
                "/api/trace", "/api/agents/{slug}/inference-receipts"
            )

        async def _post(self, url: str, payload: dict) -> None:
            """Fire-and-forget POST; never raises into the caller."""
            try:
                import httpx
                token = _read_local_token()
                headers = {"Content-Type": "application/json"}
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                async with httpx.AsyncClient(timeout=3) as client:
                    await client.post(url, json=payload, headers=headers)
            except Exception as exc:
                logger.warning("litellm_callback: POST to %s failed: %s", url, exc)

        def _extract_usage(self, response: Any) -> tuple[int, int, float]:
            """Return (tokens_in, tokens_out, cost_usd) from a LiteLLM response."""
            tokens_in = 0
            tokens_out = 0
            cost_usd = 0.0
            try:
                usage = getattr(response, "usage", None)
                if usage:
                    tokens_in = getattr(usage, "prompt_tokens", 0) or 0
                    tokens_out = getattr(usage, "completion_tokens", 0) or 0
                cost = getattr(response, "_hidden_params", {})
                if isinstance(cost, dict):
                    cost_usd = float(cost.get("response_cost", 0.0) or 0.0)
            except Exception:
                pass
            return tokens_in, tokens_out, cost_usd

        def _extract_messages(self, kwargs: dict) -> list:
            try:
                msgs = kwargs.get("messages") or []
                # Truncate large message lists to keep traces bounded.
                return [
                    {"role": m.get("role", ""), "content": str(m.get("content", ""))[:2000]}
                    for m in msgs[:50]
                ]
            except Exception:
                return []

        def _extract_response_text(self, response: Any) -> str:
            try:
                choices = getattr(response, "choices", [])
                if choices:
                    msg = getattr(choices[0], "message", None)
                    if msg:
                        return str(getattr(msg, "content", "") or "")
            except Exception:
                pass
            return ""

        def _extract_slug_and_model(self, kwargs: dict) -> tuple[str, str]:
            """Resolve the agent slug from LiteLLM callback kwargs.

            LiteLLM surfaces per-key metadata on success events under
            ``litellm_params.metadata`` with several fields that all map
            back to the key the deployer minted. We try the richest
            source first (``user_api_key_metadata.agent`` is exactly
            what ``LLMProxy.create_agent_key`` wrote) and fall back
            through progressively weaker options:

              1. ``user_api_key_metadata.agent`` — the agent slug as
                 stamped into the key's metadata. Stable across LiteLLM
                 versions that echo user-supplied metadata.
              2. ``user_api_key_auth_metadata.agent`` — same payload
                 under the auth-resolved alias; present on some
                 versions but not others.
              3. ``user_api_key_alias`` — the ``taos-<slug>`` alias.
                 Stripping the prefix recovers the slug.
              4. ``key_alias`` — legacy field used by older LiteLLM
                 builds; kept for backward compat.

            Returns ``(_UNKNOWN_SLUG, model)`` when nothing matches, so
            events are still captured but bucketed under the sentinel.
            """
            litellm_params = kwargs.get("litellm_params") or {}
            metadata = litellm_params.get("metadata") or kwargs.get("metadata") or {}

            # 1+2: explicit agent slug stamped into key metadata.
            for md_key in ("user_api_key_metadata", "user_api_key_auth_metadata"):
                user_md = metadata.get(md_key)
                if isinstance(user_md, dict):
                    agent = user_md.get("agent")
                    if isinstance(agent, str) and agent:
                        return agent, str(kwargs.get("model") or "")

            # 3: derive from the ``taos-<slug>`` key alias.
            alias = metadata.get("user_api_key_alias")
            if isinstance(alias, str) and alias.startswith("taos-"):
                slug = alias[len("taos-"):]
                if slug:
                    return slug, str(kwargs.get("model") or "")

            # 4: legacy ``key_alias`` fallback for older LiteLLM builds.
            key_alias = metadata.get("key_alias") or litellm_params.get("key_alias")
            slug = _slug_from_alias(key_alias)
            return slug, str(kwargs.get("model") or "")

        async def _emit_inference_receipt(
            self,
            slug: str,
            model: str,
            kwargs: dict,
            response_obj: Any,
            start_time: Any,
            end_time: Any,
            tokens_in: int | None,
            tokens_out: int | None,
            status: str,
        ) -> None:
            """Bean-1: post a hash-only inference receipt to the controller.

            Manifest mode — sha256 digests + metadata only, never message or
            response text (docs/design/silicon-bean-integration.md). Fail-open:
            any exception is caught and logged so receipt emission can never
            break the inference path. Skipped for the unknown-slug sentinel
            (a receipt must attribute to a real bean).
            """
            try:
                if not slug or slug == _UNKNOWN_SLUG:
                    return
                prompt_hash = _prompt_hash(kwargs.get("messages") or [])
                output_text = self._extract_response_text(response_obj) if status == "success" else ""
                started_at = completed_at = None
                try:
                    if start_time is not None:
                        started_at = start_time.isoformat()
                    if end_time is not None:
                        completed_at = end_time.isoformat()
                except Exception:
                    pass
                await self._post(self._receipts_url_tmpl.format(slug=slug), {
                    "trace_id": str(kwargs.get("litellm_call_id") or "") or None,
                    "model_id": model,
                    "prompt_hash": prompt_hash,
                    "output_hash": _output_hash(output_text),
                    "prompt_tokens": tokens_in,
                    "completion_tokens": tokens_out,
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "status": status,
                })
            except Exception as exc:
                logger.warning("litellm_callback: inference receipt emission failed: %s", exc)

        def _record_spend(self, agent: str, cost_usd: float) -> None:
            """Best-effort spend increment; never raises into the caller."""
            path = os.environ.get("TAOS_AGENT_BUDGETS")
            if not path:
                return
            try:
                _budget_store_for(path).add_spend(agent, cost_usd)
            except Exception as exc:
                logger.warning("litellm_callback: budget spend increment failed: %s", exc)

        async def async_log_success_event(self, kwargs: dict, response_obj: Any, start_time: Any, end_time: Any) -> None:
            try:
                slug, model = self._extract_slug_and_model(kwargs)
                tokens_in, tokens_out, cost_usd = self._extract_usage(response_obj)
                duration_ms = 0
                try:
                    if start_time and end_time:
                        duration_ms = int((end_time - start_time).total_seconds() * 1000)
                except Exception:
                    pass
                backend_name = (kwargs.get("litellm_params") or {}).get("metadata", {}).get("backend_name") or ""
                payload = {
                    "status": "success",
                    "messages": self._extract_messages(kwargs),
                    "response": self._extract_response_text(response_obj),
                    "metadata": {
                        "model": model,
                        "backend_name": backend_name,
                    },
                }
                await self._post(self._trace_url, {
                    "agent_name": slug,
                    "kind": "llm_call",
                    "model": model,
                    "backend_name": backend_name or None,
                    "duration_ms": duration_ms,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost_usd": cost_usd,
                    "payload": payload,
                })
                if backend_name:
                    await self._post(self._notify_url, {"backend_name": backend_name})
                if cost_usd and cost_usd > 0 and slug:
                    self._record_spend(slug, cost_usd)
                await self._emit_inference_receipt(
                    slug, model, kwargs, response_obj, start_time, end_time,
                    tokens_in, tokens_out, "success",
                )
            except Exception as exc:
                logger.warning("litellm_callback: success handler error: %s", exc)

        async def async_log_failure_event(self, kwargs: dict, response_obj: Any, start_time: Any, end_time: Any) -> None:
            try:
                slug, model = self._extract_slug_and_model(kwargs)
                duration_ms = 0
                try:
                    if start_time and end_time:
                        duration_ms = int((end_time - start_time).total_seconds() * 1000)
                except Exception:
                    pass
                backend_name = (kwargs.get("litellm_params") or {}).get("metadata", {}).get("backend_name") or ""
                error_msg = str(kwargs.get("exception") or response_obj or "unknown error")
                payload = {
                    "status": "failure",
                    "messages": self._extract_messages(kwargs),
                    "response": None,
                    "metadata": {
                        "model": model,
                        "backend_name": backend_name,
                        "error": error_msg,
                    },
                }
                await self._post(self._trace_url, {
                    "agent_name": slug,
                    "kind": "llm_call",
                    "model": model,
                    "backend_name": backend_name or None,
                    "duration_ms": duration_ms,
                    "error": error_msg,
                    "payload": payload,
                })
                await self._emit_inference_receipt(
                    slug, model, kwargs, None, start_time, end_time,
                    None, None, "error",
                )
            except Exception as exc:
                logger.warning("litellm_callback: failure handler error: %s", exc)

    taos_callback = TaosLiteLLMCallback()

except ImportError:
    # LiteLLM not installed — define a no-op stub so the import never
    # fails. The proxy is optional; taOS works without it.
    logger.debug("litellm not installed — TaosLiteLLMCallback not registered")

    class _NoopCallback:  # type: ignore[no-redef]
        pass

    taos_callback = _NoopCallback()  # type: ignore[assignment]
