"""Consulta: iniciar, acompanhar (métrica unificada), reter observação, encerrar, relatório e ciclo do alerta de dor."""
from __future__ import annotations

from application.portas import GeradorDeId, Relogio, UnidadeDeTrabalho
from domain.atendimento.alerta_dor import AlertaDeDor, AlertaDeDorRecusado
from domain.atendimento.paciente import PacienteInexistente
from domain.atendimento.repositorios import RepositorioAlertaDor, RepositorioPaciente, RepositorioSessao
from domain.atendimento.sessao import Sessao, SessaoRecusada, sinais_de_dor_na_observacao


def obter_sessao(sessoes: RepositorioSessao, sessao_id: str) -> Sessao:
    sessao = sessoes.obter(sessao_id)
    if sessao is None:
        raise SessaoRecusada(sessao_id)
    return sessao


def sessao_em_andamento(sessoes: RepositorioSessao, sessao_id: str) -> Sessao:
    sessao = obter_sessao(sessoes, sessao_id)
    sessao.exigir_em_andamento()
    return sessao


class ServicoConsulta:
    def __init__(
        self,
        pacientes: RepositorioPaciente,
        sessoes: RepositorioSessao,
        alertas: RepositorioAlertaDor,
        uow: UnidadeDeTrabalho,
        relogio: Relogio,
        ids: GeradorDeId,
    ) -> None:
        self._pacientes = pacientes
        self._sessoes = sessoes
        self._alertas = alertas
        self._uow = uow
        self._relogio = relogio
        self._ids = ids

    def iniciar(self, sessao_id: str, paciente_id: str) -> None:
        if self._pacientes.obter(paciente_id) is None:
            raise PacienteInexistente(paciente_id)
        self._sessoes.adicionar(Sessao.iniciar(sessao_id, paciente_id, self._relogio.agora()))
        self._uow.commit()

    def metrica(self, sessao_id: str) -> dict:
        sessao = obter_sessao(self._sessoes, sessao_id)
        paciente = self._pacientes.obter(sessao.paciente_id)
        leitura = sessao.leitura
        return {
            "sessao_id": sessao.id,
            "paciente_id": sessao.paciente_id,
            "paciente_nome": paciente.nome if paciente else "",
            "estado": sessao.estado,
            "fala": {
                "transcricao": leitura.texto_fala,
                "termos_criticos": leitura.termos_criticos,
                "sentimento": leitura.sentimento,
            },
            "voz": {"alteracao_vocal": leitura.alteracao_vocal},
            "imagem": {"postura": leitura.postura, "face": leitura.face, "objetos_areas": leitura.objetos_areas},
            "alertas_dor": [
                {"id": a.id, "origem": a.origem, "descricao_sinal": a.descricao_sinal, "estado": a.estado}
                for a in self._alertas.da_sessao(sessao_id)
            ],
        }

    def registrar_observacao(self, sessao_id: str, obs: dict) -> dict:
        sessao = obter_sessao(self._sessoes, sessao_id).reter_observacao(obs)
        self._sessoes.salvar(sessao)
        quando = self._relogio.agora()
        for origem, descricao in sinais_de_dor_na_observacao(obs, sessao):
            self._alertas.adicionar(AlertaDeDor.abrir(self._ids.novo(), sessao_id, origem, descricao, quando))
        self._uow.commit()
        return self.metrica(sessao_id)

    def encerrar_sessao(self, sessao_id: str) -> None:
        self._sessoes.salvar(obter_sessao(self._sessoes, sessao_id).encerrar(self._relogio.agora()))
        self._uow.commit()

    def relatorio(self, sessao_id: str) -> dict:
        leitura = self.metrica(sessao_id)
        leitura["desvios"] = {
            "postura": leitura["imagem"]["postura"],
            "face": leitura["imagem"]["face"],
            "objetos_areas": leitura["imagem"]["objetos_areas"],
            "alteracao_vocal": leitura["voz"]["alteracao_vocal"],
            "termos_criticos": leitura["fala"]["termos_criticos"],
        }
        return leitura

    # --- leituras das telas Hoje e ficha do paciente -------------------------------------------
    def _nome(self, paciente_id: str) -> str:
        paciente = self._pacientes.obter(paciente_id)
        return paciente.nome if paciente else ""

    def _alertas_ativos(self, sessao_id: str) -> int:
        return sum(1 for a in self._alertas.da_sessao(sessao_id) if a.ativo)

    def em_andamento(self) -> list[dict]:
        return [
            {"sessao_id": s.id, "paciente_id": s.paciente_id, "paciente_nome": self._nome(s.paciente_id),
             "iniciada_em": s.iniciada_em, "alertas_ativos": self._alertas_ativos(s.id)}
            for s in self._sessoes.em_andamento()
        ]

    def ficha(self, paciente_id: str) -> dict:
        paciente = self._pacientes.obter(paciente_id)
        if paciente is None:
            raise PacienteInexistente(paciente_id)
        sessoes = [
            {"sessao_id": s.id, "estado": s.estado, "iniciada_em": s.iniciada_em, "encerrada_em": s.encerrada_em,
             "alertas": len(self._alertas.da_sessao(s.id)), "alertas_ativos": self._alertas_ativos(s.id)}
            for s in self._sessoes.do_paciente(paciente_id)
        ]
        andamento = next((s["sessao_id"] for s in sessoes if s["estado"] == "em_andamento"), None)
        return {"paciente": {"id": paciente.id, "nome": paciente.nome}, "sessoes": sessoes, "em_andamento": andamento}

    def alertas_de_dor_ativos(self) -> list[dict]:
        saida = []
        for alerta in self._alertas.ativos():
            sessao = self._sessoes.obter(alerta.sessao_id)
            saida.append({
                "id": alerta.id, "sessao_id": alerta.sessao_id, "origem": alerta.origem,
                "descricao_sinal": alerta.descricao_sinal, "estado": alerta.estado, "criado_em": alerta.criado_em,
                "paciente_nome": self._nome(sessao.paciente_id) if sessao else "",
            })
        return saida

    def _alerta(self, alerta_id: str) -> AlertaDeDor:
        alerta = self._alertas.obter(alerta_id)
        if alerta is None:
            raise AlertaDeDorRecusado(alerta_id)
        return alerta

    def dar_ciencia_dor(self, alerta_id: str) -> None:
        self._alertas.salvar(self._alerta(alerta_id).dar_ciencia(self._relogio.agora()))
        self._uow.commit()

    def encerrar_dor(self, alerta_id: str) -> None:
        self._alertas.salvar(self._alerta(alerta_id).encerrar(self._relogio.agora()))
        self._uow.commit()
