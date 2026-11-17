"""View models: validam e traduzem o que chega do navegador antes de chamar um caso de uso."""
from __future__ import annotations

from domain.atendimento.duvida import QUADROS_MAX, QUADROS_MIN

MAX_RECORTES = 5
MAX_BYTES_RECORTE = 200_000
ASSINATURA_JPEG = b"\xff\xd8\xff"
STATUS_DE_ALERTA = {"open", "acked", "closed"}
SIM = ("1", "true", "yes")


def blendshapes_validos(corpo: dict):
    """Só números 0..1; o resto é descartado. Devolve o valor original se não for dicionário (o caso de uso recusa)."""
    blendshapes = corpo.get("blendshapes")
    if not isinstance(blendshapes, dict):
        return blendshapes
    return {str(k): float(v) for k, v in blendshapes.items() if isinstance(v, (int, float)) and 0.0 <= float(v) <= 1.0}


def ler_recorte(arquivo) -> bytes:
    dados = arquivo.read(MAX_BYTES_RECORTE + 1)
    if len(dados) > MAX_BYTES_RECORTE:
        raise ValueError("recorte maior que 200 KB")
    if not dados.startswith(ASSINATURA_JPEG):
        raise ValueError("recorte deve ser JPEG")
    return dados


def recortes_do_formulario(arquivos) -> tuple[list[bytes], bytes | None]:
    suspeitos = arquivos.getlist("suspeitos")
    if not suspeitos or len(suspeitos) > MAX_RECORTES:
        raise ValueError(f"envie de 1 a {MAX_RECORTES} recortes")
    neutro = ler_recorte(arquivos["neutro"]) if "neutro" in arquivos else None
    return [ler_recorte(a) for a in suspeitos], neutro


def recorte_de_duvida(arquivos, formulario) -> tuple[list[bytes], float, bytes | None]:
    """Quadros da marca de atenção (2 s antes e 2 s depois) e o rosto neutro do início, se houver."""
    quadros = arquivos.getlist("quadros")
    if not QUADROS_MIN <= len(quadros) <= QUADROS_MAX:
        raise ValueError(f"envie de {QUADROS_MIN} a {QUADROS_MAX} quadros")
    try:
        duracao = float(formulario.get("duracao_s", ""))
    except ValueError as exc:
        raise ValueError("duração inválida") from exc
    neutro = ler_recorte(arquivos["neutro"]) if "neutro" in arquivos else None
    return [ler_recorte(q) for q in quadros], duracao, neutro


def status_de_alerta(valor: str | None) -> str | None:
    valor = (valor or "").strip()
    return valor if valor in STATUS_DE_ALERTA else None


def proximo_de_alertas(valor: str | None) -> str:
    destino = (valor or "/alertas").strip()
    return destino if destino.startswith("/alertas") else "/alertas"
