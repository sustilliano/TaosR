"""Standalone conftest for the Bean-3 consent tests.

Runnable without the full backend venv (aiosqlite/pytest/pytest-asyncio for
the store + policy + permissions-hook tests; fastapi/httpx additionally for
the route tests):

    pytest tests/bean_consent/ --confcutdir=tests/bean_consent

Inserts the repo root on sys.path so ``import tinyagentos`` works no matter
where pytest is invoked from. Copied from tests/inference_receipts/conftest.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
