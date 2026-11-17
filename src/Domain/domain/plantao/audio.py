"""Relatório de áudio do plantão: termos críticos da transcrição e das frases-chave."""
from __future__ import annotations

CRITICAL_STEMS = ("falta de ar", "cansad", "dor no peito", "desmaio", "sangramento", "confus")


def critical_terms(key_phrases: list[str], pontos_da_transcricao: list[dict]) -> list[str]:
    """O Azure quebra expressões ("falta de ar" vira "muita falta" + "ar"), então a transcrição
    também entra pelos pontos de atenção (regras), sem repetir termo."""
    found = [p for p in key_phrases if any(stem in p.casefold() for stem in CRITICAL_STEMS)]
    found += [p["trecho"] for p in pontos_da_transcricao]
    unique, seen = [], set()
    for term in found:
        key = term.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(term)
    return unique


def audio_report(transcript: str, analise: dict, pontos: list[dict], vocal: dict) -> dict:
    phrases = list(analise["key_phrases"])
    return {
        "transcript": transcript,
        "sentiment": analise["sentiment"],
        "key_phrases": phrases,
        "critical_terms": critical_terms(phrases, pontos),
        "attention_points": pontos,
        "vocal": vocal,
    }
