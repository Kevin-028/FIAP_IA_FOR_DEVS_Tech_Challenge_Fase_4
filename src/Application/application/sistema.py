"""Diagnóstico do sistema: o que está instalado, configurado e baixado (tela Sistema)."""
from __future__ import annotations

from typing import Protocol


class ServicoComChaves(Protocol):
    def faltando(self) -> list[str]: ...


class DetectorOpcional(Protocol):
    def disponivel(self) -> bool: ...


class InventarioDeModelos(Protocol):
    def itens(self) -> list[dict]:
        """[{'nome', 'ok', 'detalhe'}] dos pesos e bases baixados."""


def _item(nome: str, ok: bool, detalhe_ok: str, detalhe_falta: str) -> dict:
    return {"nome": nome, "ok": ok, "detalhe": detalhe_ok if ok else detalhe_falta}


class ServicoSistema:
    def __init__(self, fala: ServicoComChaves, linguagem: ServicoComChaves, estagio2: DetectorOpcional,
                 inventario: InventarioDeModelos) -> None:
        self._fala = fala
        self._linguagem = linguagem
        self._estagio2 = estagio2
        self._inventario = inventario

    def diagnostico(self) -> list[dict]:
        fala, linguagem = self._fala.faltando(), self._linguagem.faltando()
        return [
            _item("Azure Speech", not fala, "Transcrição da conversa ativa", "Falta no .env: " + ", ".join(fala)),
            _item("Azure Language", not linguagem, "Sentimento e frases-chave ativos",
                  "Falta no .env: " + ", ".join(linguagem)),
            _item("Estágio 2 da dor (Py-Feat)", self._estagio2.disponivel(), "Confirmação da dor facial ativa",
                  "Opcional: pip install -r requirements-estagio2.txt"),
            *self._inventario.itens(),
        ]

    def pendencias(self) -> int:
        return sum(1 for item in self.diagnostico() if not item["ok"])
