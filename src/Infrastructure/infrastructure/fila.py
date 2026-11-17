"""Porta FilaDeTrabalho: uma thread em segundo plano que executa uma tarefa por vez, na ordem de chegada.

O validador (Py-Feat) é pesado em CPU e memória: rodar várias avaliações juntas só deixaria todas mais lentas.
Cada tarefa usa a própria conexão SQLite desta thread, fechada ao terminar.
"""
from __future__ import annotations

import logging
import queue
import threading
from typing import Callable, Protocol

log = logging.getLogger(__name__)


class _Conexao(Protocol):
    def fechar(self) -> None: ...


class FilaEmSegundoPlano:
    def __init__(self, conexao: _Conexao, nome: str = "fila-validador") -> None:
        self._conexao = conexao
        self._nome = nome
        self._fila: queue.Queue[tuple[Callable[[], None], str]] = queue.Queue()
        self._trava = threading.Lock()
        self._thread: threading.Thread | None = None

    def enfileirar(self, tarefa: Callable[[], None], descricao: str = "") -> None:
        self._fila.put((tarefa, descricao))
        self._garantir_thread()

    def pendentes(self) -> int:
        return self._fila.unfinished_tasks  # esperando + a que está rodando

    def aguardar(self, timeout: float | None = None) -> bool:
        """Espera a fila esvaziar (testes e desligamento). True se esvaziou dentro do prazo."""
        concluida = threading.Event()
        threading.Thread(target=lambda: (self._fila.join(), concluida.set()), daemon=True).start()
        return concluida.wait(timeout)

    def _garantir_thread(self) -> None:
        with self._trava:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._trabalhar, name=self._nome, daemon=True)
                self._thread.start()

    def _trabalhar(self) -> None:
        while True:
            tarefa, descricao = self._fila.get()
            try:
                tarefa()
            except Exception:  # uma tarefa quebrada não pode parar as próximas
                log.exception("tarefa da fila falhou: %s", descricao)
            finally:
                try:
                    self._conexao.fechar()
                finally:
                    self._fila.task_done()
