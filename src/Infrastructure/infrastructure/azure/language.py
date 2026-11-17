"""Azure AI Language (Text Analytics): sentimento e key phrases."""
from __future__ import annotations

import os

import requests

from infrastructure.azure.speech import AzureNotConfigured


def language_configured() -> bool:
    return bool(os.environ.get("AZURE_LANGUAGE_KEY") and os.environ.get("AZURE_LANGUAGE_ENDPOINT"))


def missing_language() -> list[str]:
    missing = []
    if not os.environ.get("AZURE_LANGUAGE_KEY"):
        missing.append("AZURE_LANGUAGE_KEY")
    if not os.environ.get("AZURE_LANGUAGE_ENDPOINT"):
        missing.append("AZURE_LANGUAGE_ENDPOINT")
    return missing


def analyze_text(text: str, language: str = "pt") -> dict:
    missing = missing_language()
    if missing:
        raise AzureNotConfigured(missing)
    key = os.environ["AZURE_LANGUAGE_KEY"]
    endpoint = os.environ["AZURE_LANGUAGE_ENDPOINT"].rstrip("/")
    url = f"{endpoint}/language/:analyze-text?api-version=2023-04-01"
    headers = {"Ocp-Apim-Subscription-Key": key}

    def _post(kind: str) -> dict:
        response = requests.post(
            url,
            headers=headers,
            json={
                "kind": kind,
                "analysisInput": {"documents": [{"id": "1", "language": language, "text": text}]},
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["results"]["documents"][0]

    return {
        "sentiment": _post("SentimentAnalysis")["sentiment"],
        "key_phrases": _post("KeyPhraseExtraction")["keyPhrases"],
    }


class AnalisadorAzure:
    """Porta AnalisadorDeTexto (Azure Text Analytics)."""

    def configurado(self) -> bool:
        return language_configured()

    def faltando(self) -> list[str]:
        return missing_language()

    def analisar(self, texto: str) -> dict:
        return analyze_text(texto)
