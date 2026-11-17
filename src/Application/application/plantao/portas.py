"""Portas do contexto Plantão: fala, voz, vídeo, outlier vital e base PhysioNet."""
from __future__ import annotations

from typing import Protocol

from application.atendimento.portas import ServicoExternoNaoConfigurado


class AudioSemServicoExterno(ServicoExternoNaoConfigurado):
    """Azure ausente: o relatório não sai, mas os traços vocais já calculados vão junto."""

    def __init__(self, missing: list[str], vocal: dict):
        super().__init__(missing)
        self.vocal = vocal


class Transcritor(Protocol):
    def faltando(self) -> list[str]: ...
    def transcrever(self, caminho_wav: str) -> str: ...


class AnalisadorDeTextoPlantao(Protocol):
    def faltando(self) -> list[str]: ...
    def analisar(self, texto: str) -> dict: ...


class AnalisadorDeVoz(Protocol):
    def ler_wav(self, caminho: str) -> tuple[object, int]:
        """Amostras mono normalizadas e taxa; ValueError se não for PCM 16-bit."""
    def caracteristicas(self, amostras: object, taxa: int) -> dict: ...


class AnalisadorDeVideo(Protocol):
    def analisar(self, caminho: str) -> tuple[dict, str | None]:
        """Relatório de postura e área crítica, mais um aviso quando um modelo está ausente."""


class DetectorDeOutliers(Protocol):
    def detectar(self, matriz: list[list[float]]) -> list[int]: ...


class FonteDeSeries(Protocol):
    """Base do PhysioNet Challenge 2019 usada pelo plantão de demonstração."""

    def serie(self, record: str) -> dict | None: ...
    def paciente_padrao(self) -> str: ...
