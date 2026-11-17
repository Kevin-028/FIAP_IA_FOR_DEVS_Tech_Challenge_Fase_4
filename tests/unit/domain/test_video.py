"""Vídeo: ângulo, desvio postural, zonas e relatório (sem MediaPipe/YOLO)."""
from __future__ import annotations

import pytest

from domain.plantao.pose import joint_angle_deg, posture_deviations, shoulder_abduction_deg
from domain.plantao.video_report import OPENPOSE_NOTE, build_video_report
from domain.plantao.zones import zone_events

SAFE = (0.2, 0.2, 0.6, 0.6)
FIELD = (0.3, 0.3, 0.3, 0.3)


def _frame(left_elbow, right_elbow):
    """Ombros em y=0.4, quadris em y=0.8; o cotovelo define a abdução."""
    points = [(0.0, 0.0, 0.0)] * 33
    points[11], points[23], points[13] = (0.4, 0.4, 0.0), (0.4, 0.8, 0.0), left_elbow
    points[12], points[24], points[14] = (0.6, 0.4, 0.0), (0.6, 0.8, 0.0), right_elbow
    return points


BRACO_ACIMA = (0.4, 0.1, 0.0)      # 180° esquerdo
BRACO_ACIMA_D = (0.6, 0.1, 0.0)    # 180° direito
BRACO_LATERAL_E = (0.1, 0.4, 0.0)  # 90° esquerdo
BRACO_LATERAL_D = (0.9, 0.4, 0.0)  # 90° direito
BRACO_BAIXO_D = (0.6, 0.7, 0.0)    # ~0° direito


@pytest.mark.parametrize(
    ("a", "b", "c", "esperado"),
    [((1, 0), (0, 0), (0, 1), 90.0), ((1, 0), (0, 0), (-1, 0), 180.0), ((1, 0), (0, 0), (1, 0), 0.0)],
)
def test_angulo_entre_tres_pontos(a, b, c, esperado):
    assert joint_angle_deg(a, b, c) == pytest.approx(esperado, abs=1e-6)


def test_angulo_com_pontos_coincidentes_nao_divide_por_zero():
    assert 0.0 <= joint_angle_deg((0, 0), (0, 0), (1, 1)) <= 180.0


def test_abducao_do_ombro_por_lado():
    frame = _frame(BRACO_LATERAL_E, BRACO_ACIMA_D)
    assert shoulder_abduction_deg(frame, "left") == pytest.approx(90, abs=1)
    assert shoulder_abduction_deg(frame, "right") == pytest.approx(180, abs=1)


def test_exercicio_correto_nao_gera_desvio():
    assert posture_deviations([_frame(BRACO_LATERAL_E, BRACO_LATERAL_D)]) == []


def test_desvios_overshoot_undershoot_e_assimetria():
    kinds = {d["kind"] for d in posture_deviations([_frame(BRACO_ACIMA, BRACO_ACIMA_D)])}
    assert kinds == {"overshoot"}
    baixo = _frame((0.4, 0.7, 0.0), BRACO_BAIXO_D)
    assert {d["kind"] for d in posture_deviations([baixo])} == {"undershoot"}
    assim = {d["kind"] for d in posture_deviations([_frame(BRACO_LATERAL_E, BRACO_BAIXO_D)])}
    assert "asymmetry" in assim


def test_objeto_critico_no_campo_e_pessoa_fora_da_area():
    eventos = zone_events(
        [
            {"label": "cell phone", "bbox": (0.35, 0.35, 0.1, 0.1), "conf": 0.8},
            {"label": "person", "bbox": (0.85, 0.85, 0.1, 0.1), "conf": 0.9},
            {"label": "person", "bbox": (0.4, 0.4, 0.2, 0.2), "conf": 0.9},
            {"label": "cup", "bbox": (0.35, 0.35, 0.1, 0.1), "conf": 0.9},
        ],
        safe_rect=SAFE,
        field_rect=FIELD,
    )
    assert [e["kind"] for e in eventos] == ["critical_object", "left_safe_zone"]


def test_relatorio_de_video_resume_eventos():
    vazio = build_video_report(exercise="ombro", frame_count=10, deviations=[], zone_events=[])
    assert vazio["summary"] == "Sem desvio em ombro."
    cheio = build_video_report(exercise="ombro", frame_count=10, deviations=[{}], zone_events=[{}, {}])
    assert cheio["summary"].startswith("Desvio detectado em 3")
    assert cheio["models"] == ["mediapipe-pose", "yolov8n"]
    assert cheio["openpose_note"] == OPENPOSE_NOTE
