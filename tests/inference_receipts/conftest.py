"""Standalone conftest for the Bean-1 inference-receipt tests.

Runnable without the full backend venv (aiosqlite/pytest/pytest-asyncio for
the store + callback-hash tests; fastapi/httpx additionally for the routes):

    pytest tests/inference_receipts/ --confcutdir=tests/inference_receipts

Inserts the repo root on sys.path so ``import tinyagentos`` works no matter
where pytest is invoked from.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
