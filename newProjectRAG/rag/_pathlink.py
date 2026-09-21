"""Makes backend/'s `app` package importable from this project without
packaging backend/ or duplicating its dependencies.

This project is meant to run inside backend's own virtualenv (see
../README.md) and just needs backend/ on sys.path to reuse its DB session,
models, config, and Anthropic client. Every module here that imports from
`app.*` imports this module first.
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
