"""Fase 4: série, desvio, anomalia, fusão e rotas."""
from __future__ import annotations

import wave

import numpy as np

from hospital.db import (
    ack_alert,
    close_alert,
    connect,
    emit_alert,
    get_alert,
    init_db,
    list_movement,
    list_prescriptions,
    list_vitals,
)
from hospital.seed_fase4 import apply
from multimodal.audio_pipeline import audio_report
from multimodal.azure_speech import AzureNotConfigured, transcribe_wav
from multimodal.evaluate import run
from multimodal.fusion import fuse
from multimodal.monitor import tick
from multimodal.movement import movement_anomalies
from multimodal.pose import posture_deviations
from multimodal.prescriptions import prescription_anomalies
from multimodal.video_report import OPENPOSE_NOTE
from multimodal.vitals import vital_anomalies
from multimodal.vocal import vocal_features
from multimodal.zones import zone_events
from scripts.make_demo_audio import wav_is_demo


def test_seed_usa_registro_da_base(tmp_path):
    conn = connect(str(tmp_path / "h.db"))
    init_db(conn)
    apply(conn)
    alert = list_vitals(conn, "p000003")
    stable = list_vitals(conn, "p000057")
    assert len(alert) <= 36
    assert any(row["spo2"] < 92 or row["dbp"] < 50 or row["hr"] > 120 for row in alert)
    assert stable
    assert all(row["spo2"] >= 92 and 45 <= row["hr"] <= 120 for row in stable)
    drugs = prescription_anomalies(list_prescriptions(conn, "p000003"))
    assert "high_alert_start" in {item["rule"] for item in drugs}
    assert "dose_jump" in {item["rule"] for item in drugs}
    moves = movement_anomalies(list_movement(conn, "p000003"))
    assert "immobility" in {item["rule"] for item in moves}
    assert "night_exit" in {item["rule"] for item in moves}
    conn.close()


def test_postura_e_zona():
    frame = [(0.0, 0.0, 0.0)] * 33
    frame[11] = (0.4, 0.4, 0.0)
    frame[23] = (0.4, 0.8, 0.0)
    frame[13] = (0.4, 0.1, 0.0)
    frame[12] = (0.6, 0.4, 0.0)
    frame[24] = (0.6, 0.8, 0.0)
    frame[14] = (0.6, 0.1, 0.0)
    assert posture_deviations([frame])[0]["kind"] == "overshoot"
    events = zone_events(
        [{"label": "cell phone", "bbox": (0.35, 0.35, 0.1, 0.1), "conf": 0.8}],
        safe_rect=(0.2, 0.2, 0.6, 0.6),
        field_rect=(0.3, 0.3, 0.3, 0.3),
    )
    assert events[0]["kind"] == "critical_object"


def test_fadiga_e_termo_critico():
    rate = 16000
    tone = 0.2 * np.sin(2 * np.pi * 220 * np.arange(rate) / rate)
    feat = vocal_features(np.concatenate([tone, np.zeros(rate)]), rate)
    assert feat["fatigue"] is True
    report = audio_report(
        "consulta.wav",
        transcribe=lambda _path: "estou com falta de ar",
        analyze=lambda _text: {"sentiment": "negative", "key_phrases": ["falta de ar"]},
        samples=np.zeros(rate),
        sample_rate=rate,
    )
    assert report["critical_terms"] == ["falta de ar"]


def test_anomalias_e_fusao_sem_prescrever(tmp_path):
    vitals = vital_anomalies([
        {"recorded_at": "2026-04-05T01:00:00+00:00", "hr": 132, "sbp": 120, "dbp": 80, "spo2": 88},
    ])
    assert {item["rule"] for item in vitals} >= {"spo2_low", "hr_high"}
    drugs = prescription_anomalies([
        {"recorded_at": "2026-04-03T08:00:00+00:00", "drug": "varfarina", "dose_mg": 5, "route": "oral", "action": "start"},
        {"recorded_at": "2026-04-03T20:00:00+00:00", "drug": "AAS", "dose_mg": 300, "route": "oral", "action": "change"},
    ])
    assert "high_alert_start" in {item["rule"] for item in drugs}
    rows = [{"recorded_at": f"2026-04-05T{hour}:00:00+00:00", "posture": "supine", "zone": "bed"} for hour in range(18, 24)]
    rows += [{"recorded_at": f"2026-04-06T0{hour}:00:00+00:00", "posture": "supine", "zone": "bed"} for hour in range(0, 3)]
    assert "immobility" in {item["rule"] for item in movement_anomalies(rows)}
    result = fuse(
        video={"deviations": [{"detail": "abducao 160 graus"}], "zone_events": []},
        audio={"sentiment": "negative", "critical_terms": ["falta de ar"], "vocal": {"fatigue": True, "respiratory_effort": False}},
        vitals=vitals,
        prescriptions=drugs,
        movement=[],
        chart_text="nota",
    )
    assert result["level"] == "high"
    assert result["prescribes"] is False
    conn = connect(str(tmp_path / "h.db"))
    init_db(conn)
    out = tick(
        conn,
        "PAC-0002",
        vital={"recorded_at": "2026-04-05T05:00:00+00:00", "hr": 132, "sbp": 120, "dbp": 80, "spo2": 88},
        movement=None,
    )
    assert any(reason.startswith("Sinal vital spo2") for reason in out["new_alerts"])
    conn.close()


def test_azure_sem_chave(monkeypatch, tmp_path):
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF")
    try:
        transcribe_wav(str(wav))
        assert False
    except AzureNotConfigured as exc:
        assert "AZURE_SPEECH_KEY" in exc.missing


def test_resultados_citam_datasets():
    result = run()
    assert result["video"]["summary"].startswith("Desvio detectado")
    assert result["video"]["openpose_note"] == OPENPOSE_NOTE
    assert result["fusion"]["prescribes"] is False
    assert "https://physionet.org/" in result["datasets"]["urls"]


def test_wav_demo(tmp_path):
    path = tmp_path / "consulta.wav"
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(np.zeros(16000, dtype=np.int16).tobytes())
    assert wav_is_demo(str(path)) is True


def test_paginas_fase4(client):
    for url in ("/fase4", "/fase4/video", "/fase4/audio", "/fase4/anomalias", "/fase4/monitor", "/alertas"):
        response = client.get(url)
        assert response.status_code == 200, url
    home = client.get("/fase4")
    assert b"p000003" in home.data
    assert b"educacional" in home.data.lower() or b"PhysioNet" in home.data or b"Demo" in home.data


def test_ack_e_close_alerta(tmp_path):
    conn = connect(str(tmp_path / "alerts.db"))
    init_db(conn)
    assert emit_alert(
        conn,
        patient_id="p000003",
        thread_id="fase4-p000003",
        severity="high",
        reason="teste spo2",
        source="fase4.vitals",
    )
    row = conn.execute("SELECT id FROM alerts").fetchone()
    alert_id = int(row["id"])
    acked = ack_alert(conn, alert_id)
    assert acked["status"] == "acked"
    assert acked["acked_at"]
    closed = close_alert(conn, alert_id)
    assert closed["status"] == "closed"
    assert closed["closed_at"]
    assert get_alert(conn, alert_id)["status"] == "closed"
    conn.close()


def test_rotas_ack_close(client):
    from hospital.db import connect, emit_alert, get_alert, init_db

    conn = connect()
    init_db(conn)
    emit_alert(
        conn,
        patient_id="p000003",
        thread_id="fase4-p000003-ui",
        severity="high",
        reason="alerta ui demo",
        source="fase4.vitals",
    )
    alert_id = int(conn.execute("SELECT id FROM alerts WHERE reason = ?", ("alerta ui demo",)).fetchone()["id"])
    conn.close()
    assert client.post(f"/alertas/{alert_id}/ack", data={"next": "/alertas?status=acked"}).status_code == 302
    conn = connect()
    assert get_alert(conn, alert_id)["status"] == "acked"
    conn.close()
    assert client.post(f"/alertas/{alert_id}/close", data={"next": "/alertas?status=closed"}).status_code == 302
    conn = connect()
    assert get_alert(conn, alert_id)["status"] == "closed"
    conn.close()


_NAV_FLAGS = (
    "nav_multimodal",
    "nav_video",
    "nav_audio",
    "nav_anomalias",
    "nav_monitor",
    "nav_alertas",
)

_NAV_ATIVO_POR_ROTA = {
    "/fase4": "nav_multimodal",
    "/fase4/video": "nav_video",
    "/fase4/audio": "nav_audio",
    "/fase4/anomalias": "nav_anomalias",
    "/fase4/monitor": "nav_monitor",
    "/alertas": "nav_alertas",
}


def test_nav_ativo_somente_na_rota_correspondente(client, app):
    """Context processor: um flag True por rota; /fase4/* não compartilha o mesmo flag."""
    from flask import template_rendered

    for url, ativo in _NAV_ATIVO_POR_ROTA.items():
        capturados = []

        def _capturar(sender, template, context, **extra):
            capturados.append(dict(context))

        with template_rendered.connected_to(_capturar, app):
            response = client.get(url)
        assert response.status_code == 200, url
        assert capturados, f"nenhum template renderizado em {url}"
        ctx = capturados[0]
        for flag in _NAV_FLAGS:
            esperado = flag == ativo
            assert ctx.get(flag) is esperado, (
                f"{url}: {flag}={ctx.get(flag)!r}, esperado {esperado}"
            )


def test_audio_sem_azure(client, monkeypatch, tmp_path):
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)
    monkeypatch.delenv("AZURE_LANGUAGE_KEY", raising=False)
    monkeypatch.delenv("AZURE_LANGUAGE_ENDPOINT", raising=False)
    path = tmp_path / "c.wav"
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(np.zeros(16000, dtype=np.int16).tobytes())
    with open(path, "rb") as handle:
        response = client.post(
            "/api/fase4/audio",
            data={"patient_id": "p000003", "file": (handle, "c.wav")},
            content_type="multipart/form-data",
        )
    assert response.status_code == 503
    assert response.get_json()["error"] == "azure_nao_configurado"


def test_publicar_anomalias(client):
    response = client.post(
        "/api/fase4/anomalias/alertas",
        json={"patient_id": "p000003"},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["prescribes"] is False
    assert body["level"] == "high"
    assert isinstance(body["new_alerts"], list)
