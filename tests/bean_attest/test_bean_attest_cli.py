"""Tests for the Bean-5 attestation CLI (tinyagentos/bean_attest_cli.py).

Invokes the CLI as a subprocess (``python -m tinyagentos.bean_attest_cli``)
against a tmp --data-dir seeded with a signed receipt + provenance record,
exactly the way an external holder would run it — no HTTP, no running
controller.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tinyagentos import bean_keystore
from tinyagentos.agent_provenance_store import AgentProvenanceStore
from tinyagentos.inference_receipt_store import InferenceReceiptStore

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_ID = "hermes-3-llama-3.1-8b"
MODEL_FILE_SHA256 = "d4403ce5a6e930f4c2509456388c20d633a15ff08dd52ef3b142ff1810ec3553"

PROVENANCE_RECORD = {
    "substrate": "silicon",
    "framework": "hermes",
    "framework_ref": "v0.2.1",
    "installer_sha256": "a" * 64,
    "constitution_sha256": "b" * 64,
    "model_id": MODEL_ID,
    "model_file_sha256": MODEL_FILE_SHA256,
    "corpus_refs": ["https://huggingface.co/datasets/teknium/OpenHermes-2.5"],
    "recorded_at": "2026-07-24T00:00:00Z",
}


def _seed(data_dir: Path, agent: str = "scout-1") -> str:
    """Seed a signed receipt + provenance record under data_dir; return the
    inference_id. Runs its own event loop (this is a sync helper for
    non-async test functions)."""

    async def _do():
        receipt_store = InferenceReceiptStore(
            data_dir / "agent-memory" / agent / "receipts.sqlbook"
        )
        await receipt_store.init()
        inference_id = await receipt_store.record(
            model_id=MODEL_ID,
            prompt_hash="e" * 64,
            output_hash="f" * 64,
            trace_id="call-1",
            prompt_tokens=10,
            completion_tokens=20,
            started_at="2026-07-24T00:00:00+00:00",
            completed_at="2026-07-24T00:00:01+00:00",
            status="success",
            signer=lambda r: bean_keystore.sign_receipt(agent, data_dir, r),
        )
        await receipt_store.close()

        prov_store = AgentProvenanceStore(data_dir / "agent_provenance.db")
        await prov_store.init()
        await prov_store.set_provenance(agent, PROVENANCE_RECORD)
        await prov_store.close()
        return inference_id

    return asyncio.run(_do())


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "tinyagentos.bean_attest_cli", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestHelp:
    def test_help_works(self):
        proc = _run_cli("--help")
        assert proc.returncode == 0
        assert "usage" in proc.stdout.lower()


class TestFullWalk:
    def test_verified_prints_and_exits_0(self, tmp_path):
        inference_id = _seed(tmp_path, "scout-1")
        proc = _run_cli("scout-1", inference_id, "--data-dir", str(tmp_path))
        assert proc.returncode == 0
        assert "verified" in proc.stdout.lower()
        assert "signature" in proc.stdout
        assert "provenance_present" in proc.stdout
        assert "model_binding" in proc.stdout
        assert "constitution" in proc.stdout
        assert "corpus" in proc.stdout

    def test_json_output_is_parseable(self, tmp_path):
        inference_id = _seed(tmp_path, "scout-1")
        proc = _run_cli("scout-1", inference_id, "--data-dir", str(tmp_path), "--json")
        assert proc.returncode == 0
        body = json.loads(proc.stdout)
        assert body["agent"] == "scout-1"
        assert body["inference_id"] == inference_id
        assert body["overall"] == "verified"
        assert len(body["links"]) == 5
        assert all(link["status"] == "pass" for link in body["links"])

    def test_unknown_inference_id_exits_nonzero(self, tmp_path):
        _seed(tmp_path, "scout-1")
        proc = _run_cli("scout-1", "inf-doesnotexist", "--data-dir", str(tmp_path))
        assert proc.returncode == 1
        assert "error" in proc.stderr.lower()

    def test_unknown_agent_exits_nonzero(self, tmp_path):
        proc = _run_cli("ghost-agent", "inf-doesnotexist", "--data-dir", str(tmp_path))
        assert proc.returncode == 1
