"""Pontos de atenção numa fala da consulta. Marca o trecho; não diagnostica nem prescreve."""
from __future__ import annotations

import re
import unicodedata

ALTA = "alta"
MEDIA = "media"

_NUMEROS = r"(?:\d+|um|uma|uns|umas|dois|duas|tres|quatro|cinco|seis|sete|oito|nove|dez|alguns|algumas|muitos|muitas)"

# (categoria, severidade, motivo, padrão sobre texto minúsculo e sem acento).
# A ordem é a prioridade: um achado específico cobre o genérico no mesmo trecho.
_REGRAS: tuple[tuple[str, str, str, str], ...] = (
    ("Risco à vida", ALTA, "Relato de ideação suicida ou de não querer viver",
     r"me matar|suicid\w*|nao quero mais viver|acabar com (?:a )?minha vida|tirar (?:a )?minha vida"),
    ("Dor torácica", ALTA, "Dor ou aperto no peito é sinal de alarme",
     r"dor no peito|dores no peito|aperto no peito|dor no coracao|peito apertado"),
    ("Dificuldade respiratória", ALTA, "Queixa respiratória",
     r"falta de ar|sem ar|nao consigo respirar|dificuldade (?:para|de|pra) respirar|sem folego|ofegante|respiracao curta"),
    ("Sinal neurológico", ALTA, "Possível sinal de AVC ou déficit neurológico",
     r"formigamento|dormencia|boca torta|fala enrolada|enrolando a fala|fraqueza (?:no|num|em um) lado|nao sinto o (?:braco|lado)|perdi a forca"),
    ("Perda de consciência", ALTA, "Desmaio ou perda de consciência",
     r"desmai\w*|apaguei|perdi (?:a )?consciencia"),
    ("Convulsão", ALTA, "Relato de convulsão", r"convuls\w*|ataque epileptico|me debati"),
    ("Sangramento", ALTA, "Relato de sangramento", r"sangr\w*|sangue|hemorragi\w*"),
    ("Alteração cognitiva", ALTA, "Confusão ou desorientação", r"confus[ao]\w*|desorientad\w*"),
    ("Falha de adesão", ALTA, "Paciente parou ou esqueceu a medicação",
     r"parei de tomar|esqueci de tomar|nao tomei|nao estou tomando|deixei de tomar|abandonei o (?:remedio|tratamento)"),
    ("Alergia", ALTA, "Alergia relatada", r"alergi\w*|alergico|alergica"),
    ("Intensidade da dor", ALTA, "Dor relatada em escala numérica",
     r"\b(?:[7-9]|10)\s*(?:de|em)\s*10\b"),
    ("Dor", MEDIA, "Queixa de dor",
     r"\bdor\b|\bdores\b|pontada\w*|latej\w*|queimacao|ardencia|doendo|\bdoi\b|\bdoe\b"),
    ("Febre", MEDIA, "Febre ou calafrio", r"febre|febril|calafrio\w*"),
    ("Fadiga", MEDIA, "Cansaço ou fraqueza",
     r"cansad[oa]\w*|cansaco|fadiga|exaust[oa]\w*|sem energia|fraqueza|sem forca"),
    ("Tontura", MEDIA, "Tontura ou vertigem", r"tontura\w*|tont[oa]\b|vertigem"),
    ("Náusea ou vômito", MEDIA, "Náusea ou vômito", r"vomit\w*|nausea\w*|enjo[oa]\w*|enjoad[oa]"),
    ("Tosse", MEDIA, "Tosse", r"tosse\w*|tossindo"),
    ("Medicação", MEDIA, "Medicação citada na consulta",
     r"remedio\w*|medicament\w*|comprimido\w*|antibiotico\w*|anticoagulante\w*|varfarina|insulina|\bdose\b"),
    ("Tempo de evolução", MEDIA, "Há quanto tempo o quadro começou",
     r"(?:\bha|\bfaz|desde ha)\s+(?:uns\s+|umas\s+)?" + _NUMEROS
     + r"\s+(?:horas?|dias?|semanas?|mes|meses|anos?)\b"
     r"|desde (?:ontem|anteontem|a semana passada|semana passada|o mes passado|mes passado)"),
)

_COMPILADAS = tuple(
    (categoria, severidade, motivo, re.compile(padrao))
    for categoria, severidade, motivo, padrao in _REGRAS
)

# Categorias cujo padrão já carrega a negação ("não consigo respirar").
_NEGACAO_FAZ_PARTE = {"Dificuldade respiratória", "Falha de adesão", "Risco à vida", "Sinal neurológico"}
_NEGACAO = re.compile(r"\b(?:nao|nunca|nem|sem|nenhuma?)\b(?:\s+\w+){0,2}\s*$")


def _sem_acento(texto: str) -> str:
    """Minúsculo sem acento, um caractere por caractere: os índices batem com o original."""
    saida = []
    for char in texto:
        base = unicodedata.normalize("NFD", char)[0]
        saida.append(base.lower() if len(base.lower()) == 1 else char)
    return "".join(saida)


def _negado(normal: str, inicio: int) -> bool:
    return bool(_NEGACAO.search(normal[max(0, inicio - 30):inicio]))


def pontos_por_regra(texto: str) -> list[dict]:
    normal = _sem_acento(texto)
    achados: list[dict] = []
    ocupados: list[tuple[int, int]] = []
    vistos: set[str] = set()
    for categoria, severidade, motivo, padrao in _COMPILADAS:
        if categoria in vistos:
            continue
        for match in padrao.finditer(normal):
            inicio, fim = match.span()
            if any(a <= inicio and fim <= b for a, b in ocupados):
                continue
            if categoria not in _NEGACAO_FAZ_PARTE and _negado(normal, inicio):
                continue
            achados.append({
                "categoria": categoria,
                "severidade": severidade,
                "motivo": motivo,
                "trecho": texto[inicio:fim],
                "inicio": inicio,
                "origem": "regra",
            })
            ocupados.append((inicio, fim))
            vistos.add(categoria)
            break
    achados.sort(key=lambda item: item["inicio"])
    return achados


def pontos_por_azure(texto: str, sentimento: str, frases_chave: list[str]) -> list[dict]:
    if sentimento != "negative":
        return []
    trecho = ", ".join(frases_chave[:3]) if frases_chave else texto[:160]
    return [{
        "categoria": "Sentimento negativo",
        "severidade": MEDIA,
        "motivo": "Azure Text Analytics classificou a fala como negativa",
        "trecho": trecho,
        "inicio": 0,
        "origem": "azure",
    }]
