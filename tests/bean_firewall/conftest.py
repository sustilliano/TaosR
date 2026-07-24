"""Standalone conftest for the Bean-4 cognitive-firewall tests.

Runnable without the full backend venv (aiosqlite/pytest/pytest-asyncio for
the core + store tests; fastapi/httpx additionally for the route tests):

    pytest tests/bean_firewall/ --confcutdir=tests/bean_firewall

Inserts the repo root on sys.path so ``import tinyagentos`` works no matter
where pytest is invoked from. Copied from tests/bean_consent/conftest.py /
tests/provenance/conftest.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
