"""Azure Speech to Text via REST."""
from __future__ import annotations

import os

import requests


class AzureNotConfigured(RuntimeError):
    def __init__(self, missing: list[str]):
        super().__init__("azure_nao_configurado")
        self.missing = missing


def speech_configured() -> bool:
    return bool(os.environ.get("AZURE_SPEECH_KEY") and os.environ.get("AZURE_SPEECH_REGION"))


def missing_speech() -> list[str]:
    missing = []
    if not os.environ.get("AZURE_SPEECH_KEY"):
        missing.append("AZURE_SPEECH_KEY")
    if not os.environ.get("AZURE_SPEECH_REGION"):
        missing.append("AZURE_SPEECH_REGION")
    return missing


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
