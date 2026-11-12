"""Fusão de texto, áudio, vídeo e anomalias. Não prescreve."""
from __future__ import annotations


def fuse(*, video, audio, vitals, prescriptions, movement, chart_text: str = "") -> dict:
    findings = []
    if video:
        for item in video.get("deviations") or []:
            findings.append({
                "source": "fase4.video",
                "severity": "high",
                "reason": f"Desvio postural: {item['detail']}",
            })
        for item in video.get("zone_events") or []:
            findings.append({
                "source": "fase4.video",
                "severity": "high",
                "reason": f"Area critica: {item['detail']}",
            })
    if audio:
        vocal = audio.get("vocal") or {}
        if vocal.get("fatigue"):
            findings.append({"source": "fase4.audio", "severity": "high", "reason": "Fadiga vocal"})
        if vocal.get("respiratory_effort"):
            findings.append({
                "source": "fase4.audio",
                "severity": "high",
                "reason": "Esforco respiratorio na fala",
            })
        if audio.get("sentiment") == "negative":
            for term in audio.get("critical_terms") or []:
                findings.append({
                    "source": "fase4.audio",
                    "severity": "high",
                    "reason": f"Sentimento negativo com termo critico: {term}",
                })
    for item in vitals:
        findings.append({
            "source": "fase4.vitals",
            "severity": "high",
            "reason": f"Sinal vital {item['signal']} {item['value']} em {item['recorded_at']}",
        })
    for item in prescriptions:
        findings.append({
            "source": "fase4.prescription",
            "severity": "high",
            "reason": f"Prescricao: {item['detail']}",
        })
    for item in movement:
        findings.append({
            "source": "fase4.movement",
            "severity": "high",
            "reason": f"Movimentacao: {item['detail']}",
        })
    return {
        "level": "high" if findings else "low",
        "findings": findings,
        "prescribes": False,
        "chart_excerpt": (chart_text or "")[:500],
    }
