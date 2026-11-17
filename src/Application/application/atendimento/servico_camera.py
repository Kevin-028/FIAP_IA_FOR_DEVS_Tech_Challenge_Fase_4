"""Estágio 1 da câmera: leitura facial por segundo, eventos estáveis, suspeita de dor e alerta sem estágio 2."""
from __future__ import annotations

from application.atendimento.portas import Estagio2
from application.atendimento.servico_consulta import sessao_em_andamento
from application.portas import GeradorDeId, Relogio, UnidadeDeTrabalho
from domain.atendimento import cascata
from domain.atendimento.alerta_dor import AlertaDeDor
from domain.atendimento.dor_facial import LEITURAS_BASE, classificar_expressao, linha_de_base, pspi
from domain.atendimento.repositorios import (
    RepositorioAlertaDor,
    RepositorioConfirmacaoDor,
    RepositorioEventoFace,
    RepositorioLeituraFace,
    RepositorioSessao,
)


def alerta_face_ativo(alertas: RepositorioAlertaDor, sessao_id: str) -> bool:
    return any(a.origem == "face" and a.ativo for a in alertas.da_sessao(sessao_id))


class ServicoCamera:
    def __init__(
        self,
        sessoes: RepositorioSessao,
        leituras: RepositorioLeituraFace,
        eventos: RepositorioEventoFace,
        confirmacoes: RepositorioConfirmacaoDor,
        alertas: RepositorioAlertaDor,
        estagio2: Estagio2,
        uow: UnidadeDeTrabalho,
        relogio: Relogio,
        ids: GeradorDeId,
    ) -> None:
        self._sessoes = sessoes
        self._leituras = leituras
        self._eventos = eventos
        self._confirmacoes = confirmacoes
        self._alertas = alertas
        self._estagio2 = estagio2
        self._uow = uow
        self._relogio = relogio
        self._ids = ids

    def _evento(self, sessao_id: str, quando: str, tipo: str, expressao: str, descricao: str) -> dict:
        evento = {"id": self._ids.novo(), "registrado_em": quando, "tipo": tipo, "expressao": expressao,
                  "descricao": descricao}
        self._eventos.adicionar(sessao_id, evento)
        return evento

    def abrir_alerta_face(self, sessao_id: str, quando: str, descricao: str, expressao: str, evento: str) -> dict:
        self._alertas.adicionar(AlertaDeDor.abrir(self._ids.novo(), sessao_id, "face", descricao, quando))
        return self._evento(sessao_id, quando, "dor", expressao, evento)

    def registrar_leitura(self, sessao_id: str, blendshapes: dict, *, registrado_em: str | None = None) -> dict:
        """Com estágio 2 disponível, o alerta só abre na confirmação; sem ele, vale dor moderada sustentada."""
        sessao = sessao_em_andamento(self._sessoes, sessao_id)
        if not isinstance(blendshapes, dict) or not blendshapes:
            raise ValueError("blendshapes ausentes")
        estagio2 = self._estagio2.disponivel()
        quando = registrado_em or self._relogio.agora()
        iniciais = self._leituras.pspi_iniciais(sessao_id, LEITURAS_BASE)
        if len(iniciais) < LEITURAS_BASE:
            iniciais.append(pspi(blendshapes))
        leitura = {**classificar_expressao(blendshapes, base_pspi=linha_de_base(iniciais)),
                   "id": self._ids.novo(), "registrado_em": quando}
        self._leituras.adicionar(sessao_id, leitura)
        recentes = self._leituras.recentes(sessao_id, cascata.RECENTES)

        eventos = []
        anterior = self._eventos.ultima_expressao(sessao_id) or "neutra"
        descricao = cascata.evento_de_expressao(recentes, anterior, leitura["expressao"])
        if descricao:
            eventos.append(self._evento(sessao_id, quando, "expressao", leitura["expressao"], descricao))

        alerta = False
        aberto = alerta_face_ativo(self._alertas, sessao_id)
        suspeita = cascata.suspeita(recentes)  # o navegador grava a marca e, com estágio 2, pede o veredito
        if not estagio2 and cascata.dor_sustentada(recentes) and not aberto:
            descricao = f"expressao facial de dor sustentada (PSPI +{leitura['dor_relativa']:.1f} sobre a linha de base)"
            eventos.append(self.abrir_alerta_face(sessao_id, quando, descricao, leitura["expressao"],
                                                  "Expressão de dor sustentada no rosto do paciente"))
            alerta = True

        rotulo = cascata.rotulo(leitura)
        self._sessoes.salvar(sessao.com_face(rotulo))
        self._uow.commit()
        return {"leitura": {**leitura, "rotulo": rotulo}, "eventos_novos": eventos, "alerta_dor": alerta,
                "suspeita": suspeita, "estagio2": estagio2}

    def expressao_recente(self, sessao_id: str, *, agora: str | None = None) -> str:
        """Rótulo da última leitura facial, se ela tiver até JANELA_FALA_S segundos."""
        ultima = self._leituras.ultima(sessao_id)
        if ultima is None or not cascata.expressao_vale_para_fala(ultima["registrado_em"], agora or self._relogio.agora()):
            return ""
        return cascata.rotulo(ultima)

    def leitura_atual(self, sessao_id: str) -> dict | None:
        ultima = self._leituras.ultima(sessao_id)
        return {**ultima, "rotulo": cascata.rotulo(ultima)} if ultima else None

    def eventos(self, sessao_id: str) -> list[dict]:
        return self._eventos.da_sessao(sessao_id)
