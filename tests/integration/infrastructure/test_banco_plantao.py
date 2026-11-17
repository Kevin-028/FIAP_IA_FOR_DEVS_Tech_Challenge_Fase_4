"""Plantão no SQLite: seed PhysioNet, monitor tick a tick e ciclo do alerta."""
from __future__ import annotations

from domain.plantao.movement import movement_anomalies
from domain.plantao.prescriptions import prescription_anomalies
from infrastructure.persistencia.banco import connect, emit_alert, get_alert, list_movement, list_prescriptions, list_vitals
from infrastructure.persistencia.seed import apply


def test_seed_usa_registro_da_base(tmp_path):
    conn = connect(str(tmp_path / "h.db"))
    apply(conn)
    alerta = list_vitals(conn, "p000003")
    estavel = list_vitals(conn, "p000057")
    assert 0 < len(alerta) <= 36
    assert any(r["spo2"] < 92 or r["dbp"] < 50 or r["hr"] > 120 for r in alerta)
    assert estavel and all(r["spo2"] >= 92 and 45 <= r["hr"] <= 120 for r in estavel)
    drogas = {a["rule"] for a in prescription_anomalies(list_prescriptions(conn, "p000003"))}
    assert {"high_alert_start", "dose_jump"} <= drogas
    movimentos = {a["rule"] for a in movement_anomalies(list_movement(conn, "p000003"))}
    assert {"immobility", "night_exit"} <= movimentos
    conn.close()


def test_seed_e_idempotente(tmp_path):
    conn = connect(str(tmp_path / "h.db"))
    apply(conn)
    antes = len(list_vitals(conn, "p000003"))
    apply(conn)
    assert len(list_vitals(conn, "p000003")) == antes
    conn.close()


def test_tick_publica_alerta_uma_vez(servicos):
    ponto = {"recorded_at": "2026-04-05T05:00:00+00:00", "hr": 132, "sbp": 120, "dbp": 80, "spo2": 88}
    primeiro = servicos.plantao.tick("PAC-T", vital=ponto, movement=None)
    assert primeiro["level"] == "high"
    assert any(r.startswith("Sinal vital spo2") for r in primeiro["new_alerts"])
    segundo = servicos.plantao.tick("PAC-T", vital=None, movement=None)
    assert not any(r.startswith("Sinal vital spo2") for r in segundo["new_alerts"])  # sem duplicar


def test_reset_monitor_limpa_serie_e_alertas(conn, servicos):
    servicos.plantao.tick("PAC-R", vital={"recorded_at": "2026-04-05T05:00:00+00:00", "hr": 40, "sbp": 120, "dbp": 80, "spo2": 97},
         movement={"recorded_at": "2026-04-05T05:00:00+00:00", "posture": "supine", "zone": "bed"})
    servicos.plantao.resetar_monitor("PAC-R")
    assert list_vitals(conn, "PAC-R") == [] and list_movement(conn, "PAC-R") == []
    assert conn.execute("SELECT COUNT(*) FROM alerts WHERE thread_id = 'fase4-PAC-R'").fetchone()[0] == 0


def test_ack_e_close_alerta(conn, servicos):
    assert emit_alert(conn, patient_id="p000003", thread_id="fase4-teste", severity="high",
                      reason="teste spo2", source="fase4.vitals")
    alert_id = int(conn.execute("SELECT id FROM alerts WHERE reason = 'teste spo2'").fetchone()["id"])
    servicos.alertas.reconhecer(alert_id)
    acked = get_alert(conn, alert_id)
    assert acked["status"] == "acked" and acked["acked_at"]
    servicos.alertas.fechar(alert_id)
    closed = get_alert(conn, alert_id)
    assert closed["status"] == "closed" and closed["closed_at"]


def test_migracoes_versionadas_aplicadas(conn):
    versoes = {r["id"] for r in conn.execute("SELECT id FROM schema_migrations")}
    assert {"001_consultorio", "002_transcricao", "003_interlocutores_camera", "004_cascata_dor"} <= versoes


def test_tick_avalia_a_medicao_ao_vivo(servicos):
    normal = {"recorded_at": "2026-04-05T05:00:00+00:00", "hr": 80, "sbp": 120, "dbp": 80, "spo2": 97}
    assert servicos.plantao.tick("PAC-V", vital=normal, movement=None)["avaliacao"]["estado"] == "normal"
    baixa = {**normal, "recorded_at": "2026-04-05T06:00:00+00:00", "spo2": 88}
    avaliacao = servicos.plantao.tick("PAC-V", vital=baixa, movement=None)["avaliacao"]
    assert avaliacao == {"estado": "fora_da_faixa", "motivos": ["SpO2 88 abaixo de 92"]}
    assert servicos.plantao.tick("PAC-V", vital=None, movement=None)["avaliacao"] is None
