"""Pytest — Fase 4. Unitários em tests/unit, integração em tests/integration."""
from __future__ import annotations

import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")

for path in (WEB_DIR, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)


def pytest_addoption(parser):
    parser.addoption(
        "--azure",
        action="store_true",
        default=False,
        help="roda os testes que chamam o Azure de verdade (usa as chaves do .env)",
    )


def _azure_ligado(config) -> bool:
    return config.getoption("--azure") or os.environ.get("RUN_AZURE_TESTS") == "1"


def pytest_collection_modifyitems(config, items):
    pular_azure = pytest.mark.skip(reason="teste com Azure real: use --azure ou RUN_AZURE_TESTS=1")
    for item in items:
        caminho = str(item.fspath).replace("\\", "/")
        if "/tests/unit/" in caminho:
            item.add_marker(pytest.mark.unit)
        elif "/tests/integration/" in caminho:
            item.add_marker(pytest.mark.integration)
        if "azure" in item.keywords and not _azure_ligado(config):
            item.add_marker(pular_azure)


@pytest.fixture(scope="session")
def project_root() -> str:
    return PROJECT_ROOT
