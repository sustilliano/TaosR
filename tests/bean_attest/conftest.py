"""Standalone conftest for the Bean-5 attestation-walk tests.

Runnable without the full backend venv (aiosqlite/pytest/pytest-asyncio for
the walk + CLI tests; fastapi/httpx additionally for the route tests;
cryptography for bean_keystore signing):

    pytest tests/bean_attest/ --confcutdir=tests/bean_attest

Inserts the repo root on sys.path so ``import tinyagentos`` works no matter
where pytest is invoked from.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
