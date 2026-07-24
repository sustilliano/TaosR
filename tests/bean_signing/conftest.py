"""Standalone conftest for the Bean-2 receipt-signing tests.

Runnable without the full backend venv:

    pytest tests/bean_signing/ --confcutdir=tests/bean_signing

Inserts the repo root on sys.path so ``import tinyagentos`` works no matter
where pytest is invoked from.  Same trick as tests/inference_receipts/conftest.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
