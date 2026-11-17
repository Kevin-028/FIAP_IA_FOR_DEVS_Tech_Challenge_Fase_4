"""Agregado Sessão: a conversa de um paciente cadastrado. Em andamento ou encerrada; não reabre (RN-06, RN-09)."""
from __future__ import annotations

from dataclasses import dataclass, field, replace

EM_ANDAMENTO = "em_andamento"
ENCERRADA = "encerrada"


class SessaoRecusada(Exception):
    pass


@dataclass(frozen=True)
class LeituraDaSessao:
    """O que a sessão retém para a métrica e o relatório. Sem vital, prescrição, veracidade ou escore."""

    texto_fala: str = ""
    termos_criticos: str = ""
    sentimento: str = ""
    alteracao_vocal: str = ""
    postura: str = ""
    face: str = ""
    objetos_areas: str = ""


def _limpo(valor) -> str:
    return (valor or "").strip()


@dataclass(frozen=True)
class Sessao:
    id: str
    paciente_id: str
    estado: str = EM_ANDAMENTO
    leitura: LeituraDaSessao = field(default_factory=LeituraDaSessao)
    iniciada_em: str = ""
    encerrada_em: str | None = None

    @classmethod
    def iniciar(cls, sessao_id: str, paciente_id: str, quando: str) -> "Sessao":
        return cls(sessao_id, paciente_id, EM_ANDAMENTO, LeituraDaSessao(), quando)

    @property
    def em_andamento(self) -> bool:
        return self.estado == EM_ANDAMENTO

    def exigir_em_andamento(self) -> None:
        if not self.em_andamento:
            raise SessaoRecusada("sessao encerrada")

    def encerrar(self, quando: str) -> "Sessao":
        if not self.em_andamento:
            raise SessaoRecusada(self.id)
        return replace(self, estado=ENCERRADA, encerrada_em=quando)

    def _com(self, **campos) -> "Sessao":
        return replace(self, leitura=replace(self.leitura, **campos))

    def reter_observacao(self, obs: dict) -> "Sessao":
        """Observação da captura: acumula a fala; demais campos só trocam quando vierem preenchidos."""
        self.exigir_em_andamento()
        termos = obs.get("termos_criticos") or ""
        if isinstance(termos, list):
            termos = ", ".join(termos)
        novos = {
            "termos_criticos": termos,
            "sentimento": _limpo(obs.get("sentimento")),
            "alteracao_vocal": _limpo(obs.get("alteracao_vocal")),
            "postura": _limpo(obs.get("postura")),
            "face": _limpo(obs.get("face")),
            "objetos_areas": _limpo(obs.get("objetos_areas")),
        }
        texto = (self.leitura.texto_fala + " " + _limpo(obs.get("texto"))).strip()
        return self._com(texto_fala=texto, **{k: v for k, v in novos.items() if v})

    def acrescentar_fala(self, texto: str, sentimento: str, papel: str) -> "Sessao":
        """Sentimento do médico não vira sentimento da conversa."""
        campos = {"texto_fala": (self.leitura.texto_fala + " " + texto).strip()}
        if sentimento and papel != "medico":
            campos["sentimento"] = sentimento
        return self._com(**campos)

    def com_termos(self, termos: str) -> "Sessao":
        return self._com(termos_criticos=termos)

    def com_face(self, rotulo: str) -> "Sessao":
        return self._com(face=rotulo)


def sinais_de_dor_na_observacao(obs: dict, sessao: Sessao) -> list[tuple[str, str]]:
    """Origens de dor de uma observação (RN-13): face com dor, mancando, pontada. Uma basta."""
    fala = sessao.leitura.texto_fala.casefold()
    face = (obs.get("face") or "").casefold()
    postura = (obs.get("postura") or "").casefold()
    sinais = []
    if obs.get("face_dor") or "dor na face" in face:
        sinais.append(("face", "face com dor"))
    if obs.get("mancando") or "mancando" in fala or "mancando" in postura:
        sinais.append(("movimentacao", "mancando"))
    if "pontada" in fala:
        sinais.append(("relato", "pontada"))
    return sinais
