"""Standalone conftest for the TMrFS memory-tier bridge tests.

    pytest tests/tmrfs/ --confcutdir=tests/tmrfs

Puts the repo root on sys.path so the bridge (which itself imports the
mcp_stdio helper from robotics/) resolves.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
