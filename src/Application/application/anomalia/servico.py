"""Casos de uso do contexto Anomalia de padrão: treinar no corpus e avaliar uma série."""
from __future__ import annotations

from application.anomalia.portas import CorpusVital, MotorDeAnomalia
from application.portas import GeradorDeId, Relogio, UnidadeDeTrabalho
from domain.anomalia.alerta import AlertaDeAnomalia, leitura_de_anomalia
from domain.anomalia.modelo import ModeloAusente, ModeloDeAnomalia, nomear_sinais, recusar_faixa_fixa
from domain.anomalia.repositorios import RepositorioAlertaAnomalia, RepositorioModelo


class ServicoAnomalia:
    def __init__(
        self,
        modelos: RepositorioModelo,
        alertas: RepositorioAlertaAnomalia,
        motor: MotorDeAnomalia,
        corpus: CorpusVital,
        uow: UnidadeDeTrabalho,
        relogio: Relogio,
        ids: GeradorDeId,
    ) -> None:
        self._modelos = modelos
        self._alertas = alertas
        self._motor = motor
        self._corpus = corpus
        self._uow = uow
        self._relogio = relogio
        self._ids = ids

    def treinar(self, modelo_id: str) -> str:
        linhas = self._corpus.linhas_de_treino()
        if len(linhas) < 24:
            raise ModeloAusente("corpus insuficiente")
        modelo = ModeloDeAnomalia.treinado(modelo_id, self._motor.treinar(linhas), len(linhas), self._relogio.agora())
        self._modelos.adicionar(modelo)
        self._uow.commit()
        return modelo_id

    def alertas(self) -> list[dict]:
        return self._alertas.listar()

    def listar_modelos(self) -> list[dict]:
        return self._modelos.listar()

    def avaliar_serie(self, modelo_id: str, serie_id: str, linhas: list[dict]) -> dict:
        modelo = self._modelos.obter(modelo_id)
        if modelo is None:
            raise ModeloAusente(modelo_id)
        modelo.exigir_utilizavel()
        picos = self._motor.picos_anomalos(modelo.artefato, linhas)
        alerta = None
        if picos is not None:
            alerta = AlertaDeAnomalia.abrir(self._ids.novo(), serie_id, modelo_id, nomear_sinais(picos),
                                            self._relogio.agora())
            self._alertas.adicionar(alerta)
            self._uow.commit()
        return leitura_de_anomalia(serie_id, modelo_id, alerta)

    def avaliar_serie_do_corpus(self, modelo_id: str, serie_id: str) -> dict | None:
        """None quando a série não está no corpus."""
        linhas = self._corpus.serie(serie_id)
        if linhas is None:
            return None
        return self.avaliar_serie(modelo_id, serie_id, linhas)

    def avaliar_faixa_fixa(self) -> None:
        recusar_faixa_fixa()
