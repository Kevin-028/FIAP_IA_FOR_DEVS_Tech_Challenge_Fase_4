"""Marca de atenção da dor facial (ADR-004): cada suspeita do estágio 1 vira um recorte de 2 a 4 s para o médico.

O recorte fica disponível na hora. O veredito do estágio 2 chega depois e só auxilia; quem classifica é o médico.
Um falso negativo custa mais que um recorte a mais, por isso nenhuma suspeita depende do validador para ser vista.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from domain.atendimento.dor_facial import DESCRICAO_WONG_BAKER, DOR_MODERADA

MARGEM_DO_LIMIAR = 1.0
DURACAO_MIN_S, DURACAO_MAX_S = 2.0, 4.0
QUADROS_MIN, QUADROS_MAX = 2, 40          # até 4 s a 10 quadros por segundo
QUADROS_DO_VALIDADOR = 3                   # o estágio 2 avalia o centro do recorte: o momento da suspeita
VEREDITOS = {
    "avaliando": "Avaliando…",
    "confirmada": "Validador confirmou dor",
    "descartada": "Validador descartou",
    "sem_resultado": "Validador sem resultado",
}
CATEGORIAS = {"dor": "Dor", "sem_dor": "Sem dor", "outra_expressao": "Outra expressão", "imagem_ruim": "Imagem ruim"}
OBSERVACAO_MAX = 500


def quadros_do_validador(total: int) -> list[int]:
    """Índices dos quadros que o estágio 2 avalia: os do meio do recorte (2 s antes | suspeita | 2 s depois)."""
    quantos = min(QUADROS_DO_VALIDADOR, total)
    inicio = max(0, (total - quantos + 1) // 2)
    return list(range(inicio, inicio + quantos))


def perto_do_limiar(dor_relativa: float | None) -> bool:
    return dor_relativa is not None and abs(dor_relativa - DOR_MODERADA) <= MARGEM_DO_LIMIAR


@dataclass(frozen=True)
class DuvidaDeDor:
    id: str
    sessao_id: str
    criado_em: str
    duracao_s: float
    quadros: int
    wong_baker_estimado: int | None = None   # estágio 1, no momento da suspeita
    dor_relativa: float | None = None
    veredito: str = "avaliando"
    confirmacao_id: str | None = None
    veredito_face: int | None = None
    veredito_dor_relativa: float | None = None
    veredito_em: str | None = None
    face_classificada: int | None = None
    categoria: str | None = None
    observacao: str | None = None
    classificada_em: str | None = None

    @classmethod
    def registrar(cls, *, duvida_id, sessao_id, criado_em, duracao_s, quadros, wong_baker_estimado=None,
                  dor_relativa=None) -> "DuvidaDeDor":
        if not DURACAO_MIN_S <= float(duracao_s) <= DURACAO_MAX_S:
            raise ValueError("o recorte deve ter de 2 a 4 segundos")
        if not QUADROS_MIN <= int(quadros) <= QUADROS_MAX:
            raise ValueError(f"o recorte deve ter de {QUADROS_MIN} a {QUADROS_MAX} quadros")
        return cls(duvida_id, sessao_id, criado_em, round(float(duracao_s), 2), int(quadros),
                   None if wong_baker_estimado is None else int(wong_baker_estimado),
                   None if dor_relativa is None else float(dor_relativa))

    @property
    def pendente(self) -> bool:
        return self.classificada_em is None

    @property
    def avaliando(self) -> bool:
        return self.veredito == "avaliando"

    @property
    def perto_do_limiar(self) -> bool:
        return perto_do_limiar(self.veredito_dor_relativa)

    @property
    def veredito_texto(self) -> str:
        texto = VEREDITOS[self.veredito]
        if self.veredito == "confirmada":
            texto += f" · face {self.veredito_face}"
        elif self.veredito == "descartada":
            texto += f" (+{self.veredito_dor_relativa:.1f})"
        return texto + (" · perto do limiar" if self.perto_do_limiar else "")

    def _exige_avaliando(self) -> None:
        if not self.avaliando:
            raise ValueError("o validador já deu o veredito desta marca")

    def com_veredito(self, confirmacao: dict, quando: str) -> "DuvidaDeDor":
        self._exige_avaliando()
        return replace(self, veredito="confirmada" if confirmacao["confirmado"] else "descartada",
                       confirmacao_id=confirmacao["id"], veredito_face=int(confirmacao["wong_baker"]),
                       veredito_dor_relativa=float(confirmacao["dor_relativa"]), veredito_em=quando)

    def sem_resultado(self, quando: str) -> "DuvidaDeDor":
        """Validador ausente, ocupado ou sem rosto nos recortes: a marca continua valendo para o médico."""
        self._exige_avaliando()
        return replace(self, veredito="sem_resultado", veredito_em=quando)

    def classificar(self, face, categoria: str, observacao: str, quando: str) -> "DuvidaDeDor":
        """O médico pode rever a própria classificação; a última vale."""
        if isinstance(face, bool) or face not in DESCRICAO_WONG_BAKER:
            raise ValueError("face Wong-Baker deve ser 0, 2, 4, 6, 8 ou 10")
        if categoria not in CATEGORIAS:
            raise ValueError("categoria inválida")
        nota = (observacao or "").strip()
        if len(nota) > OBSERVACAO_MAX:
            raise ValueError(f"observação com mais de {OBSERVACAO_MAX} caracteres")
        return replace(self, face_classificada=face, categoria=categoria, observacao=nota or None, classificada_em=quando)
