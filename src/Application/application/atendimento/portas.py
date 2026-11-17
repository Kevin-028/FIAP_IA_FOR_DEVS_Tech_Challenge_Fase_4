"""Portas do contexto Atendimento: estágio 2 da dor facial e serviços de linguagem."""
from __future__ import annotations

from typing import Protocol


class ServicoExternoNaoConfigurado(RuntimeError):
    """Serviço externo (Azure) sem as variáveis de ambiente; `missing` lista quais."""

    def __init__(self, missing: list[str]):
        super().__init__("azure_nao_configurado")
        self.missing = missing


class Estagio2Indisponivel(RuntimeError):
    """O detector do estágio 2 não está instalado (o app roda só o estágio 1)."""


class AvaliadorIndisponivel(RuntimeError):
    """O estágio 2 está instalado mas não carregou (pesos ausentes, versão incompatível)."""


class Estagio2(Protocol):
    """Detector de Action Units sobre recortes JPEG do rosto (Py-Feat na Infrastructure)."""

    nome: str

    def disponivel(self) -> bool: ...

    def avaliar(self, imagens: list[bytes]) -> list[dict | None]:
        """AUs (0..1) por imagem, na mesma ordem; None quando não há rosto."""


class ArmazemDeQuadros(Protocol):
    """Recortes JPEG das dúvidas, guardados só neste computador."""

    def guardar(self, duvida_id: str, quadros: list[bytes]) -> None: ...

    def ler(self, duvida_id: str, indice: int) -> bytes | None: ...


class AnalisadorDeTexto(Protocol):
    """Sentimento e frases-chave (Azure Text Analytics na Infrastructure)."""

    def configurado(self) -> bool: ...

    def analisar(self, texto: str) -> dict:
        """{'sentiment': str, 'key_phrases': list[str]}"""


class EmissorDeTokenDeFala(Protocol):
    """Token curto para o SDK de fala no navegador; a chave nunca sai do servidor."""

    def emitir(self) -> dict: ...
