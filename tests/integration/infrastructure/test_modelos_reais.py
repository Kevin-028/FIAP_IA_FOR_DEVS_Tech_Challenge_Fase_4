"""MediaPipe Pose e YOLOv8 de verdade, e o vídeo ponta a ponta pela rota Flask."""
from __future__ import annotations

import os

import numpy as np
import pytest

from infrastructure.ia.yolo import YOLO_WEIGHTS
from infrastructure.ia.mediapipe_pose import POSE_MODEL

pytestmark = pytest.mark.models

precisa_pose = pytest.mark.skipif(not os.path.isfile(POSE_MODEL), reason="rode python scripts/download_pose.py")
precisa_yolo = pytest.mark.skipif(not os.path.isfile(YOLO_WEIGHTS), reason="rode python scripts/download_yolo.py")


@precisa_pose
def test_pose_retorna_33_keypoints_em_foto_com_pessoa(foto_com_pessoas):
    from infrastructure.ia.mediapipe_pose import landmarks_of

    pontos = landmarks_of(foto_com_pessoas)
    assert pontos is not None and len(pontos) == 33
    assert all(len(p) == 3 for p in pontos)


@precisa_pose
def test_pose_retorna_none_sem_pessoa():
    from infrastructure.ia.mediapipe_pose import landmarks_of

    assert landmarks_of(np.zeros((240, 320, 3), dtype=np.uint8)) is None


@precisa_yolo
def test_yolo_detecta_pessoas_com_bbox_normalizada(foto_com_pessoas):
    from infrastructure.ia.yolo import detections_of

    deteccoes = detections_of(foto_com_pessoas)
    pessoas = [d for d in deteccoes if d["label"] == "person"]
    assert len(pessoas) >= 2
    for d in deteccoes:
        x, y, w, h = d["bbox"]
        assert 0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1
        assert 0 < d["conf"] <= 1


@precisa_pose
@precisa_yolo
def test_video_ponta_a_ponta_pela_rota(client, foto_com_pessoas, tmp_path):
    cv2 = pytest.importorskip("cv2")
    clip = str(tmp_path / "clip.mp4")
    h, w = foto_com_pessoas.shape[:2]
    writer = cv2.VideoWriter(clip, cv2.VideoWriter_fourcc(*"mp4v"), 10, (w, h))
    for _ in range(10):
        writer.write(foto_com_pessoas)
    writer.release()

    with open(clip, "rb") as handle:
        r = client.post("/api/fase4/video/arquivo", data={"file": (handle, "clip.mp4"), "patient_id": "p000003"},
                        content_type="multipart/form-data")
    assert r.status_code == 200
    body = r.get_json()
    assert body["warning"] is None and body["prescribes"] is False
    report = body["report"]
    assert report["frame_count"] == 2  # amostra 1 a cada 5 frames
    assert report["deviations"] or report["zone_events"]
    assert body["new_alerts"]


def _jpeg(imagem) -> bytes:
    import cv2

    ok, dados = cv2.imencode(".jpg", imagem)
    assert ok
    return dados.tobytes()


@pytest.mark.parametrize("versao", ["v1", "v2"])
def test_estagio2_pyfeat_le_aus_do_pspi_e_ignora_imagem_sem_rosto(versao):
    pytest.importorskip("feat", reason="rode pip install -r requirements-estagio2.txt")
    import cv2

    from infrastructure.ia.pyfeat import AUS_PSPI, AvaliadorPyFeat
    from feat.utils.io import get_test_data_path

    rosto = cv2.imread(os.path.join(get_test_data_path(), "single_face.jpg"))
    vazio = np.full((256, 256, 3), 127, dtype=np.uint8)
    com_rosto, sem_rosto = AvaliadorPyFeat(versao).avaliar([_jpeg(rosto), _jpeg(vazio)])
    assert set(AUS_PSPI) <= set(com_rosto) and all(0.0 <= v <= 1.0 for v in com_rosto.values())
    assert sem_rosto is None


def test_estagio2_v2_nao_confirma_dor_num_sorriso():
    pytest.importorskip("feat", reason="rode pip install -r requirements-estagio2.txt")
    import cv2

    from domain.atendimento.cascata import avaliar_confirmacao
    from infrastructure.ia.pyfeat import AvaliadorPyFeat
    from feat.utils.io import get_test_data_path

    sorriso = cv2.imread(os.path.join(get_test_data_path(), "single_face.jpg"))
    out = avaliar_confirmacao("py-feat v2", AvaliadorPyFeat("v2").avaliar([_jpeg(sorriso)]), None)
    assert out["confirmado"] is False and out["detector"] == "py-feat v2"


def test_estagio2_mantem_o_modelo_entre_pedidos_e_libera_no_encerramento():
    pytest.importorskip("feat", reason="rode pip install -r requirements-estagio2.txt")
    from infrastructure.ia.pyfeat import AvaliadorPyFeat

    vazio = _jpeg(np.full((256, 256, 3), 127, dtype=np.uint8))
    avaliador = AvaliadorPyFeat("v2", ociosidade_s=120)
    assert avaliador.carregado is False
    avaliador.avaliar([vazio])
    modelo = avaliador._modelo.obter()
    avaliador.avaliar([vazio])
    assert avaliador._modelo.obter() is modelo  # o segundo pedido não recarrega
    avaliador.liberar()
    assert avaliador.carregado is False
