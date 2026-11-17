"""Azure Speech to Text via REST."""
from __future__ import annotations

import os

import requests

from application.atendimento.portas import ServicoExternoNaoConfigurado


class AzureNotConfigured(ServicoExternoNaoConfigurado):
    """Azure sem chave/região no .env (porta: ServicoExternoNaoConfigurado)."""


def speech_configured() -> bool:
    return bool(os.environ.get("AZURE_SPEECH_KEY") and os.environ.get("AZURE_SPEECH_REGION"))


def missing_speech() -> list[str]:
    missing = []
    if not os.environ.get("AZURE_SPEECH_KEY"):
        missing.append("AZURE_SPEECH_KEY")
    if not os.environ.get("AZURE_SPEECH_REGION"):
        missing.append("AZURE_SPEECH_REGION")
    return missing


def issue_speech_token() -> dict:
    """Token de 10 min para o SDK no navegador. A chave nunca sai do servidor."""
    missing = missing_speech()
    if missing:
        raise AzureNotConfigured(missing)
    region = os.environ["AZURE_SPEECH_REGION"]
    response = requests.post(
        f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken",
        headers={"Ocp-Apim-Subscription-Key": os.environ["AZURE_SPEECH_KEY"]},
        timeout=10,
    )
    response.raise_for_status()
    return {"token": response.text, "region": region}


def transcribe_wav(path: str, language: str = "pt-BR") -> str:
    missing = missing_speech()
    if missing:
        raise AzureNotConfigured(missing)
    key = os.environ["AZURE_SPEECH_KEY"]
    region = os.environ["AZURE_SPEECH_REGION"]
    with open(path, "rb") as handle:
        payload = handle.read()
    response = requests.post(
        f"https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1",
        params={"language": language, "format": "detailed"},
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
        },
        data=payload,
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    if body.get("RecognitionStatus") != "Success":
        raise RuntimeError(body.get("RecognitionStatus", "speech_failed"))
    return body.get("DisplayText", "")


class EmissorDeTokenAzure:
    """Porta EmissorDeTokenDeFala."""

    def emitir(self) -> dict:
        return issue_speech_token()


class TranscritorAzure:
    """Porta Transcritor do plantão: WAV 16 kHz mono → texto."""

    def faltando(self) -> list[str]:
        return missing_speech()

    def transcrever(self, caminho_wav: str) -> str:
        return transcribe_wav(caminho_wav)
