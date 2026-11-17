"""Portas técnicas comuns aos casos de uso. Implementadas na Infrastructure, trocadas por fakes nos testes."""
from __future__ import annotations

from typing import Callable, Protocol


class Relogio(Protocol):
    def agora(self) -> str:
        """Instante atual em ISO 8601 com fuso, sem microssegundos."""


class GeradorDeId(Protocol):
    def novo(self) -> str: ...


class UnidadeDeTrabalho(Protocol):
    """Fecha a transação: o caso de uso grava vários agregados e confirma uma vez só."""

    def commit(self) -> None: ...


class FilaDeTrabalho(Protocol):
    """Trabalho pesado fora da requisição: uma tarefa por vez, na ordem em que chegou."""

    def enfileirar(self, tarefa: Callable[[], None], descricao: str = "") -> None: ...

    def pendentes(self) -> int:
        """Tarefas esperando ou em execução."""
