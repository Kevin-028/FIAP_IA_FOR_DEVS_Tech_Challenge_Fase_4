"""Transcrição, termos críticos e traços vocais."""
from __future__ import annotations

from multimodal.vocal import vocal_features

CRITICAL_STEMS = ("falta de ar", "cansad", "dor no peito", "desmaio", "sangramento", "confus")


def audio_report(wav_path: str, *, transcribe, analyze, samples, sample_rate: int) -> dict:
    transcript = transcribe(wav_path)
    text = analyze(transcript)
    phrases = list(text["key_phrases"])
    critical = [
        phrase
        for phrase in phrases
        if any(stem in phrase.casefold() for stem in CRITICAL_STEMS)
    ]
    return {
        "transcript": transcript,
        "sentiment": text["sentiment"],
        "key_phrases": phrases,
        "critical_terms": critical,
        "vocal": vocal_features(samples, sample_rate),
    }
