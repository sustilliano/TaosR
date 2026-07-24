"""Standalone conftest for the Bean-0 provenance tests.

Runnable without the full backend venv (only aiosqlite/pytest/pytest-asyncio
are required for the store tests; fastapi/httpx additionally for the route
tests):

    pytest tests/provenance/ --confcutdir=tests/provenance

Inserts the repo root on sys.path so ``import tinyagentos`` works no matter
where pytest is invoked from.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
