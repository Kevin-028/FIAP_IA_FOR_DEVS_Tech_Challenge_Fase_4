"""Cadastro do paciente: incluir, listar, corrigir o nome. A exclusão é sempre recusada."""
from __future__ import annotations

from application.portas import UnidadeDeTrabalho
from domain.atendimento.paciente import ExclusaoDePacienteRecusada, Paciente, PacienteInexistente, chave_de_busca
from domain.atendimento.repositorios import RepositorioPaciente


class ServicoCadastro:
    def __init__(self, pacientes: RepositorioPaciente, uow: UnidadeDeTrabalho) -> None:
        self._pacientes = pacientes
        self._uow = uow

    def cadastrar(self, paciente_id: str, nome: str) -> None:
        self._pacientes.adicionar(Paciente.cadastrar(paciente_id, nome))
        self._uow.commit()

    def listar(self, busca: str = "") -> list[dict]:
        chave = chave_de_busca(busca)
        return [{"id": p.id, "nome": p.nome} for p in self._pacientes.listar() if chave in chave_de_busca(p.nome)]

    def corrigir(self, paciente_id: str, nome: str) -> None:
        paciente = self._pacientes.obter(paciente_id)
        if paciente is None:
            Paciente.cadastrar(paciente_id, nome)  # nome vazio é recusado antes de "inexistente"
            raise PacienteInexistente(paciente_id)
        self._pacientes.salvar(paciente.renomear(nome))
        self._uow.commit()

    def excluir(self, paciente_id: str) -> None:
        raise ExclusaoDePacienteRecusada(paciente_id)
