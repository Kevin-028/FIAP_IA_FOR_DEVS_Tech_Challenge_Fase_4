"""Regras do plantão: vitais, prescrição, movimentação, fusão, áudio e fila de alertas."""
from __future__ import annotations

import pytest

from domain.plantao.alerta import AlertaDoPlantao, achados_para_alerta, fio_do_paciente
from domain.plantao.audio import audio_report, critical_terms
from domain.plantao.fusion import fuse
from domain.plantao.movement import movement_anomalies
from domain.plantao.prescriptions import prescription_anomalies
from domain.plantao.vitals import vital_anomalies


def _vital(hora: int, **kw):
    base = {"recorded_at": f"2026-04-05T{hora:02d}:00:00+00:00", "hr": 80, "sbp": 120, "dbp": 80, "spo2": 97}
    return {**base, **kw}


@pytest.mark.parametrize(
    ("campos", "regra"),
    [
        ({"spo2": 88}, "spo2_low"),
        ({"hr": 132}, "hr_high"),
        ({"hr": 40}, "hr_low"),
        ({"sbp": 190}, "sbp_high"),
        ({"sbp": 80}, "sbp_low"),
        ({"dbp": 120}, "dbp_high"),
        ({"dbp": 45}, "dbp_low"),
    ],
)
def test_regras_de_sinais_vitais(campos, regra):
    assert regra in {a["rule"] for a in vital_anomalies([_vital(1, **campos)])}


def test_vitais_normais_nao_alertam():
    assert vital_anomalies([_vital(h) for h in range(10)]) == []


def test_outlier_multivariado_vem_da_porta_e_exige_z_alto():
    serie = [_vital(h % 24, hr=80 + (h % 3), sbp=120 + (h % 2)) for h in range(30)]
    serie[20] = _vital(20, hr=118, sbp=175, dbp=105, spo2=93)  # dentro das faixas, mas fora do padrão
    achados = vital_anomalies(serie, lambda matriz: [3, 20])
    assert [a["rule"] for a in achados] == ["isolation_forest"]  # o ponto 3 tem z baixo e não entra


def test_sem_detector_ou_poucos_pontos_nao_ha_outlier():
    serie = [_vital(h) for h in range(30)]
    assert vital_anomalies(serie) == []
    assert vital_anomalies(serie[:10], lambda m: [0]) == []


def test_prescricao_droga_de_alerta_e_salto_de_dose():
    achados = prescription_anomalies([
        {"recorded_at": "t1", "drug": "Varfarina", "dose_mg": 5, "route": "oral", "action": "start"},
        {"recorded_at": "t2", "drug": "AAS", "dose_mg": 100, "route": "oral", "action": "start"},
        {"recorded_at": "t3", "drug": "AAS", "dose_mg": 300, "route": "oral", "action": "change"},
        {"recorded_at": "t4", "drug": "Dipirona", "dose_mg": 500, "route": "oral", "action": "start"},
    ])
    assert [(a["drug"], a["rule"]) for a in achados] == [("Varfarina", "high_alert_start"), ("AAS", "dose_jump")]


def test_movimentacao_imobilidade_e_saida_noturna():
    rows = [{"recorded_at": f"2026-04-05T{h:02d}:00:00+00:00", "posture": "supine", "zone": "bed"} for h in range(8, 14)]
    rows.append({"recorded_at": "2026-04-05T23:30:00+00:00", "posture": "standing", "zone": "corridor"})
    regras = [a["rule"] for a in movement_anomalies(rows)]
    assert regras.count("immobility") == 1 and regras.count("night_exit") == 1


def test_movimentacao_normal_nao_alerta():
    rows = [
        {"recorded_at": "2026-04-05T10:00:00+00:00", "posture": "supine", "zone": "bed"},
        {"recorded_at": "2026-04-05T11:00:00+00:00", "posture": "sitting", "zone": "chair"},
        {"recorded_at": "2026-04-05T15:00:00+00:00", "posture": "standing", "zone": "corridor"},
    ]
    assert movement_anomalies(rows) == []


def test_fusao_reune_todas_as_fontes_e_nunca_prescreve():
    result = fuse(
        video={"deviations": [{"detail": "abducao 160 graus"}], "zone_events": [{"detail": "celular"}]},
        audio={"sentiment": "negative", "critical_terms": ["falta de ar"],
               "vocal": {"fatigue": True, "respiratory_effort": True}},
        vitals=[{"signal": "spo2", "value": 88.0, "recorded_at": "t"}],
        prescriptions=[{"detail": "inicio de varfarina"}],
        movement=[{"detail": "imobilidade"}],
        chart_text="x" * 900,
    )
    fontes = {f["source"] for f in result["findings"]}
    assert fontes == {"fase4.video", "fase4.audio", "fase4.vitals", "fase4.prescription", "fase4.movement"}
    assert result["level"] == "high" and result["prescribes"] is False
    assert len(result["chart_excerpt"]) == 500
    assert achados_para_alerta(result) == result["findings"]


def test_fusao_sem_achados_e_baixa():
    result = fuse(video=None, audio={"sentiment": "positive", "critical_terms": ["x"], "vocal": {}},
                  vitals=[], prescriptions=[], movement=[])
    assert result == {"level": "low", "findings": [], "prescribes": False, "chart_excerpt": ""}
    assert achados_para_alerta(result) == []


def test_relatorio_de_audio_filtra_termos_criticos():
    report = audio_report("estou com falta de ar e cansada",
                          {"sentiment": "negative", "key_phrases": ["falta de ar", "cansada", "consulta"]}, [], {})
    assert report["critical_terms"] == ["falta de ar", "cansada"] and report["sentiment"] == "negative"


def test_termo_critico_vem_da_transcricao_quando_azure_quebra_a_expressao():
    pontos = [{"trecho": "falta de ar"}, {"trecho": "dor no peito"}]
    assert critical_terms(["muita falta", "ar", "dor", "peito"], pontos) == ["falta de ar", "dor no peito"]


def test_ciclo_do_alerta_do_plantao():
    alerta = AlertaDoPlantao(1, "p1", fio_do_paciente("p1"), "high", "spo2", "fase4.vitals", "open", "t0")
    reconhecido = alerta.reconhecer("t1")
    assert reconhecido.status == "acked" and reconhecido.acked_at == "t1"
    assert reconhecido.reconhecer("t2") == reconhecido
    fechado = alerta.fechar("t3")
    assert fechado.status == "closed" and fechado.acked_at == "t3" and fechado.closed_at == "t3"
    assert fechado.reconhecer("t4") == fechado and alerta.thread_id == "fase4-p1"


def test_avaliacao_de_cada_medicao_ao_vivo():
    from domain.plantao.vitals import FAIXAS, avaliar_medicao

    normal = _vital(1)
    assert avaliar_medicao(normal, []) == {"estado": "normal", "motivos": []}
    baixa = _vital(2, spo2=88, hr=130)
    avaliacao = avaliar_medicao(baixa, vital_anomalies([baixa]))
    assert avaliacao["estado"] == "fora_da_faixa" and avaliacao["motivos"] == ["SpO2 88 abaixo de 92", "FC 130 acima de 120"]
    atipica = _vital(3, hr=118)
    achados = [{"recorded_at": atipica["recorded_at"], "rule": "isolation_forest", "signal": "multivariate"}]
    assert avaliar_medicao(atipica, achados) == {"estado": "fora_do_padrao", "motivos": ["Combinação atípica para este paciente"]}
    assert FAIXAS["spo2"] == (92, None) and FAIXAS["hr"] == (45, 120)
