"""Referências entre projetos, como ProjectReference numa solution C#.

    Domain          -> só biblioteca padrão
    Application     -> Domain
    Infrastructure  -> Domain, Application (+ bibliotecas externas)
    Web             -> todos; só a composição (app.py e dependencias.py) toca a Infrastructure
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
PROJETOS = {"domain": "Domain", "application": "Application", "infrastructure": "Infrastructure", "web": "Web"}
PERMITIDOS = {
    "domain": {"domain"},
    "application": {"domain", "application"},
    "infrastructure": {"domain", "application", "infrastructure"},
    "web": {"domain", "application", "web", "infrastructure"},
}
COMPOSICAO_WEB = {"app.py", "dependencias.py"}
NOSSOS = set(PROJETOS)


def _imports(arquivo: Path) -> set[str]:
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    nomes = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes.update(alias.name.split(".")[0] for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
            nomes.add(no.module.split(".")[0])
    return nomes


def _arquivos(pacote: str) -> list[Path]:
    return sorted((SRC / PROJETOS[pacote] / pacote).rglob("*.py"))


@pytest.mark.parametrize("pacote", sorted(PROJETOS))
def test_projeto_existe(pacote):
    assert _arquivos(pacote), f"src/{PROJETOS[pacote]}/{pacote} vazio"


@pytest.mark.parametrize("pacote", ["domain", "application"])
def test_nucleo_so_usa_biblioteca_padrao_e_camadas_internas(pacote):
    proibidos = {}
    for arquivo in _arquivos(pacote):
        fora = {
            nome for nome in _imports(arquivo)
            if nome not in PERMITIDOS[pacote] and (nome in NOSSOS or nome not in sys.stdlib_module_names)
            and nome != "__future__"
        }
        if fora:
            proibidos[str(arquivo.relative_to(SRC))] = sorted(fora)
    assert proibidos == {}


def test_infrastructure_nao_conhece_a_web():
    usam_web = [str(a.relative_to(SRC)) for a in _arquivos("infrastructure") if "web" in _imports(a)]
    assert usam_web == []


def test_web_so_toca_infrastructure_na_composicao():
    fora = [
        str(a.relative_to(SRC)) for a in _arquivos("web")
        if "infrastructure" in _imports(a) and a.name not in COMPOSICAO_WEB
    ]
    assert fora == []
