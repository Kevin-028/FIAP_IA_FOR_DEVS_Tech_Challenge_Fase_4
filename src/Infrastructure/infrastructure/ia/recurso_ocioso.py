"""Mantém um recurso pesado (modelo de IA) em memória entre pedidos e libera depois de um tempo sem uso.

Carrega no primeiro pedido, reaproveita enquanto houver uso e devolve a memória após `ociosidade_s`
sem pedidos ou no encerramento da aplicação. Pedidos simultâneos carregam uma vez só.
"""
from __future__ import annotations

import gc
import logging
import threading
import time
from typing import Callable, Generic, TypeVar

T = TypeVar("T")
log = logging.getLogger(__name__)


class RecursoComOciosidade(Generic[T]):
    def __init__(self, carregar: Callable[[], T], *, ociosidade_s: float = 120.0,
                 relogio: Callable[[], float] = time.monotonic, agendar: bool = True) -> None:
        self._carregar = carregar
        self._ociosidade_s = ociosidade_s
        self._relogio = relogio
        self._agendar = agendar
        self._trava = threading.Lock()
        self._recurso: T | None = None
        self._ultimo_uso = 0.0
        self._temporizador: threading.Timer | None = None

    @property
    def carregado(self) -> bool:
        return self._recurso is not None

    def obter(self) -> T:
        with self._trava:
            if self._recurso is None:
                inicio = self._relogio()
                self._recurso = self._carregar()
                log.info("modelo carregado em %.1f s", self._relogio() - inicio)
            self._ultimo_uso = self._relogio()
            self._programar(self._ociosidade_s)
            return self._recurso

    def verificar_ociosidade(self) -> bool:
        """Libera se passou o prazo sem uso; senão reprograma para o tempo que falta. True se liberou."""
        with self._trava:
            if self._recurso is None:
                return False
            parado = self._relogio() - self._ultimo_uso
            if parado < self._ociosidade_s:
                self._programar(self._ociosidade_s - parado)
                return False
            self._descartar("ociosidade")
            return True

    def liberar(self) -> None:
        """Encerramento da aplicação: devolve a memória e cancela o temporizador."""
        with self._trava:
            if self._temporizador is not None:
                self._temporizador.cancel()
                self._temporizador = None
            if self._recurso is not None:
                self._descartar("encerramento")

    def _descartar(self, motivo: str) -> None:
        self._recurso = None
        gc.collect()
        log.info("modelo liberado (%s)", motivo)

    def _programar(self, segundos: float) -> None:
        if not self._agendar:
            return
        if self._temporizador is not None:
            self._temporizador.cancel()
        self._temporizador = threading.Timer(max(segundos, 0.01), self.verificar_ociosidade)
        self._temporizador.daemon = True  # não segura o processo no encerramento
        self._temporizador.start()
