"""Pytest — Fase 4."""
from __future__ import annotations

import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")

for path in (WEB_DIR, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture(scope="session")
def app():
    import app as app_module

    app_module.app.config.update(TESTING=True)
    return app_module.app


@pytest.fixture()
def client(app):
    return app.test_client()
