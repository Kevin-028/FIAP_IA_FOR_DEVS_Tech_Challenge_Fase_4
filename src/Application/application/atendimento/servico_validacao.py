"""Fila do validador (ADR-004): toda marca de atenção é avaliada pelo estágio 2, uma de cada vez, na ordem.

A marca fica disponível para o médico assim que o recorte chega. O validador roda depois, fora da requisição,
com os quadros do centro do próprio recorte, e o veredito é gravado na própria marca: nada depende do
navegador para ligar veredito e vídeo, então um veredito nunca cai na marca errada.
"""
from __future__ import annotations

import logging

from application.atendimento.servico_cascata import ServicoCascataDor
from application.atendimento.servico_duvidas import ServicoDuvidas
from application.portas import FilaDeTrabalho
from domain.atendimento.cascata import SemRostoNosRecortes
from domain.atendimento.duvida import quadros_do_validador

log = logging.getLogger(__name__)


class ServicoValidacaoDeMarcas:
    def __init__(self, duvidas: ServicoDuvidas, cascata: ServicoCascataDor, fila: FilaDeTrabalho) -> None:
        self._duvidas = duvidas
        self._cascata = cascata
        self._fila = fila

    def receber(self, sessao_id: str, quadros: list[bytes], duracao_s: float, neutro: bytes | None = None) -> dict:
        """Grava a marca (visível na hora, 'Avaliando…') e põe a avaliação dela na fila."""
        marca = self._duvidas.registrar(sessao_id, quadros, duracao_s)
        recortes = [quadros[i] for i in quadros_do_validador(len(quadros))]
        self._fila.enfileirar(lambda: self.validar(sessao_id, marca["id"], recortes, neutro), f"marca {marca['id']}")
        return {**marca, "na_fila": self._fila.pendentes()}

    def validar(self, sessao_id: str, marca_id: str, recortes: list[bytes], neutro: bytes | None) -> None:
        """Roda na vez da marca. Qualquer falha do validador vira 'sem resultado'; a marca nunca fica presa."""
        confirmacao_id = None
        if self._cascata.disponivel():
            try:
                confirmacao = self._cascata.confirmar(sessao_id, recortes, neutro, exigir_em_andamento=False)
                confirmacao_id = confirmacao["confirmacao"]["id"]
            except SemRostoNosRecortes:  # caso esperado (rosto virado, fora do quadro): sem traceback no log
                log.info("validador não achou rosto na marca %s", marca_id)
            except Exception:  # falha do modelo ou da consulta: o médico ainda tem o recorte
                log.warning("validador sem resultado para a marca %s", marca_id, exc_info=True)
        self._duvidas.registrar_veredito(sessao_id, marca_id, confirmacao_id)
