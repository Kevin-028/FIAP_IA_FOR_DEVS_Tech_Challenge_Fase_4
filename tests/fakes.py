"""Fakes em memória das portas técnicas, para testar casos de uso sem banco, rede ou IA."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


class RelogioFixo:
    def __init__(self, inicio: datetime | None = None):
        self.momento = inicio or datetime(2026, 11, 15, 10, 0, tzinfo=timezone.utc)

    def agora(self) -> str:
        return self.momento.isoformat()

    def avancar(self, segundos: float) -> None:
        self.momento += timedelta(seconds=segundos)


class IdsSequenciais:
    def __init__(self, prefixo: str = "id"):
        self.prefixo = prefixo
        self.contador = 0

    def novo(self) -> str:
        self.contador += 1
        return f"{self.prefixo}-{self.contador}"


class UnidadeDeTrabalhoFalsa:
    def __init__(self):
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1
