"""Expressão facial e indicador de dor a partir dos blendshapes do MediaPipe Face Landmarker.

O navegador extrai 52 blendshapes (0..1) do rosto; nenhuma imagem sai da máquina.
O indicador de dor segue a estrutura do PSPI (Prkachin & Solomon Pain Intensity):
    PSPI = AU4 + max(AU6, AU7) + max(AU9, AU10) + AU43      (0..16)
com cada AU de intensidade (0..5) aproximado por 5 × blendshape:
    AU4  abaixar sobrancelha  → browDown
    AU6  elevar bochecha      → cheekSquint   (zerado se há sorriso: sorriso de Duchenne)
    AU7  apertar pálpebra     → eyeSquint
    AU9  franzir nariz        → noseSneer
    AU10 elevar lábio superior→ mouthUpperUp
    AU43 fechar olhos         → eyeBlink > 0.6 (média de ~1 s, então piscar não conta)
A dor relativa vira uma face da escala Wong-Baker (0, 2, 4, 6, 8, 10). As faixas são heurísticas:
a Wong-Baker é autorrelato e nenhum estudo valida esse mapeamento a partir do PSPI.
É apoio à observação clínica, não escore validado nem diagnóstico.
"""
from __future__ import annotations

import math
from statistics import median

EXPRESSOES = ("neutra", "feliz", "triste", "dor/desconforto", "surpresa/apreensão")
LIMIAR_EXPRESSAO = 0.3
DOR_LEVE = 2.0       # PSPI acima da linha de base do próprio paciente
DOR_MODERADA = 3.5
BASE_MAXIMA = 3.0    # quem já chega com dor não pode "zerar" a régua
LEITURAS_BASE = 5
INTENSIDADE_AU = 5   # AU 0..1 → intensidade FACS 0..5
OLHOS_FECHADOS = 0.6  # AU43 conta 1 ponto acima disso
LIMIAR_SORRISO_AU12 = 0.5

# (limite superior exclusivo da dor relativa, face). Acima do último limite: face 10.
FAIXAS_WONG_BAKER = ((1.0, 0), (2.0, 2), (4.0, 4), (6.0, 6), (9.0, 8))
FACE_MAXIMA = 10
DESCRICAO_WONG_BAKER = {
    0: "sem dor",
    2: "dói um pouquinho",
    4: "dói um pouco mais",
    6: "dói ainda mais",
    8: "dói muito",
    10: "pior dor possível",
}


def _numero(valor) -> float:
    try:
        numero = float(valor or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if math.isnan(numero) else numero


def _media(bs: dict, *nomes: str) -> float:
    valores = [_numero(bs.get(nome)) for nome in nomes]
    return sum(valores) / len(valores)


def wong_baker(relativa: float) -> int:
    for limite, face in FAIXAS_WONG_BAKER:
        if relativa < limite:
            return face
    return FACE_MAXIMA


def _somar_pspi(au4: float, au6: float, au7: float, au9: float, au10: float, au43: float) -> float:
    valor = (INTENSIDADE_AU * au4 + INTENSIDADE_AU * max(au6, au7) + INTENSIDADE_AU * max(au9, au10)
             + (1.0 if au43 > OLHOS_FECHADOS else 0.0))
    return round(min(16.0, valor), 2)


def pspi_de_aus(aus: dict) -> float:
    """PSPI a partir das AUs (0..1) do estágio 2 (Py-Feat), com a mesma escala do estágio 1.

    Sorriso largo (AU12) também eleva bochecha (AU6) e lábio superior (AU10): com sorriso, os dois não contam.
    Sem essa regra, um rosto sorrindo chega a PSPI ~8,6 no Py-Feat v2.
    """
    au4, au6, au7, au9, au10, au43 = (_numero(aus.get(au)) for au in ("AU04", "AU06", "AU07", "AU09", "AU10", "AU43"))
    if _numero(aus.get("AU12")) > LIMIAR_SORRISO_AU12:
        au6 = au10 = 0.0
    return _somar_pspi(au4, au6, au7, au9, au10, au43)


def pspi(bs: dict) -> float:
    au4 = _media(bs, "browDownLeft", "browDownRight")
    au6 = _media(bs, "cheekSquintLeft", "cheekSquintRight")
    au7 = _media(bs, "eyeSquintLeft", "eyeSquintRight")
    au9 = _media(bs, "noseSneerLeft", "noseSneerRight")
    au10 = _media(bs, "mouthUpperUpLeft", "mouthUpperUpRight")
    au43 = _media(bs, "eyeBlinkLeft", "eyeBlinkRight")
    if _media(bs, "mouthSmileLeft", "mouthSmileRight") > 0.35:
        au6 = 0.0
    return _somar_pspi(au4, au6, au7, au9, au10, au43)


def linha_de_base(pspis_iniciais: list[float]) -> float:
    if not pspis_iniciais:
        return 0.0
    return round(min(BASE_MAXIMA, median(pspis_iniciais[:LEITURAS_BASE])), 2)


def nivel_dor(relativa: float) -> str:
    if relativa >= DOR_MODERADA:
        return "moderada"
    if relativa >= DOR_LEVE:
        return "leve"
    return "ausente"


def classificar_expressao(bs: dict, *, base_pspi: float = 0.0) -> dict:
    valor = pspi(bs)
    relativa = round(max(0.0, valor - base_pspi), 2)
    sorriso = _media(bs, "mouthSmileLeft", "mouthSmileRight")
    tristeza = (_media(bs, "mouthFrownLeft", "mouthFrownRight") + float(bs.get("browInnerUp", 0.0))) / 2
    if sorriso > 0.2:
        tristeza = 0.0
    surpresa = 0.7 * _media(bs, "eyeWideLeft", "eyeWideRight") + 0.3 * float(bs.get("browInnerUp", 0.0))
    scores = {
        "feliz": round(sorriso, 3),
        "triste": round(tristeza, 3),
        # escala para o limiar da expressão coincidir com o da dor leve
        "dor/desconforto": round(min(1.0, relativa * LIMIAR_EXPRESSAO / DOR_LEVE), 3),
        "surpresa/apreensão": round(surpresa, 3),
    }
    dominante = max(scores, key=scores.get)
    expressao = dominante if scores[dominante] >= LIMIAR_EXPRESSAO else "neutra"
    valencia = {"feliz": "positiva", "triste": "negativa", "dor/desconforto": "negativa"}.get(expressao, "neutra")
    return {
        "expressao": expressao,
        "valencia": valencia,
        "dor_pspi": valor,
        "dor_relativa": relativa,
        "nivel_dor": nivel_dor(relativa),
        "wong_baker": wong_baker(relativa),
        "scores": scores,
    }
