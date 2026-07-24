"""Standalone conftest for the Track 1 memory_systems tests.

Runnable without the full backend venv (only aiosqlite/pytest/pytest-asyncio
are required):

    pytest tests/memory_systems/ --confcutdir=tests/memory_systems

Inserts the repo root on sys.path so ``import tinyagentos`` works no matter
where pytest is invoked from. Copied from tests/provenance/conftest.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
