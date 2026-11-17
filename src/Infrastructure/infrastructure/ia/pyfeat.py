"""Py-Feat como estágio 2 da cascata de dor (porta Estagio2). Opcional: extra "estagio2" do projeto.

Recebe recortes JPEG do rosto, processa em memória e devolve só AUs. Nenhuma imagem é gravada.
ESTAGIO2_DETECTOR escolhe v1 ou v2; ESTAGIO2_DESLIGADO=1 força só o estágio 1.
O modelo fica em memória entre pedidos e é liberado após ESTAGIO2_OCIOSIDADE_S (padrão 120 s) sem uso
ou no encerramento da aplicação.
"""
from __future__ import annotations

import atexit
import importlib.util
import logging
import os

from application.atendimento.portas import AvaliadorIndisponivel
from infrastructure.caminhos import ROOT
from infrastructure.ia.recurso_ocioso import RecursoComOciosidade

LADO_RECORTE = 256
OCIOSIDADE_PADRAO_S = 120
DETECTORES = ("v1", "v2")
AUS_PSPI = ("AU04", "AU06", "AU07", "AU09", "AU10", "AU12", "AU43")  # AU12 só para descontar o sorriso

log = logging.getLogger(__name__)


class AvaliadorPyFeat:
    """Carrega o modelo no primeiro pedido e mantém em memória até ficar ocioso ou a aplicação encerrar."""

    def __init__(self, versao: str | None = None, ociosidade_s: float | None = None) -> None:
        versao = versao or os.environ.get("ESTAGIO2_DETECTOR", "v2")
        if versao not in DETECTORES:
            raise ValueError(f"detector deve ser um de {DETECTORES}")
        self.versao = versao
        self.nome = f"py-feat {versao}"
        espera = ociosidade_s if ociosidade_s is not None else float(
            os.environ.get("ESTAGIO2_OCIOSIDADE_S", OCIOSIDADE_PADRAO_S))
        self._modelo = RecursoComOciosidade(self._criar_detector, ociosidade_s=espera)
        atexit.register(self._modelo.liberar)

    @property
    def carregado(self) -> bool:
        return self._modelo.carregado

    def liberar(self) -> None:
        self._modelo.liberar()

    def disponivel(self) -> bool:
        if os.environ.get("ESTAGIO2_DESLIGADO") == "1":
            return False
        return importlib.util.find_spec("feat") is not None

    def _criar_detector(self):
        os.environ.setdefault("HF_HOME", os.path.join(ROOT, "models", "feat"))
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        try:
            if self.versao == "v1":
                from feat import Detectorv1
                return Detectorv1(emotion_model=None, identity_model=None, gaze_model=None, device="cpu")
            from feat import Detectorv2
            return Detectorv2(device="cpu", identity_model=None)
        except Exception as exc:  # pesos ausentes, sem internet no 1º uso, versão incompatível
            log.exception("falha ao carregar o Py-Feat %s", self.versao)
            raise AvaliadorIndisponivel(f"Py-Feat não carregou: {exc}") from exc

    def avaliar(self, imagens: list[bytes]) -> list[dict | None]:
        import torch

        lote = torch.stack([_tensor_rgb(img) for img in imagens])
        fex = self._modelo.obter().detect(lote, data_type="tensor", batch_size=len(imagens), progress_bar=False)
        return _aus_por_imagem(fex, len(imagens))


def _tensor_rgb(jpeg: bytes):
    import cv2
    import numpy as np
    import torch

    bgr = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("recorte não é uma imagem válida")
    rgb = cv2.cvtColor(cv2.resize(bgr, (LADO_RECORTE, LADO_RECORTE)), cv2.COLOR_BGR2RGB)
    return torch.from_numpy(rgb).permute(2, 0, 1).contiguous()


def _aus_por_imagem(fex, total: int) -> list[dict | None]:
    """Uma linha por rosto; fica o rosto de maior confiança de cada imagem."""
    saida: list[dict | None] = [None] * total
    melhor = [-1.0] * total
    linhas = fex.reset_index(drop=True)
    quadros = linhas["frame"] if "frame" in linhas.columns else range(len(linhas))
    for posicao, quadro in enumerate(quadros):
        linha = linhas.iloc[posicao]
        aus = {au: float(linha[au]) for au in AUS_PSPI if au in linha.index}
        if not aus or any(v != v for v in aus.values()):  # NaN = imagem sem rosto
            continue
        indice = int(quadro)
        confianca = float(linha.get("FaceScore", 0.0) or 0.0)
        if 0 <= indice < total and confianca > melhor[indice]:
            saida[indice], melhor[indice] = aus, confianca
    return saida
