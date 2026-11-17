"""Marcas de atenção da dor (ADR-004): gravar o recorte na suspeita, ligar o veredito do validador e classificar."""
from __future__ import annotations

from application.atendimento.portas import ArmazemDeQuadros
from application.atendimento.servico_consulta import sessao_em_andamento
from application.portas import GeradorDeId, Relogio, UnidadeDeTrabalho
from domain.atendimento.duvida import CATEGORIAS, DuvidaDeDor
from domain.atendimento.repositorios import (
    RepositorioConfirmacaoDor,
    RepositorioDuvida,
    RepositorioLeituraFace,
    RepositorioPaciente,
    RepositorioSessao,
)


class DuvidaInexistente(LookupError):
    pass


class ServicoDuvidas:
    def __init__(self, sessoes: RepositorioSessao, pacientes: RepositorioPaciente, leituras: RepositorioLeituraFace,
                 confirmacoes: RepositorioConfirmacaoDor, duvidas: RepositorioDuvida, armazem: ArmazemDeQuadros,
                 uow: UnidadeDeTrabalho, relogio: Relogio, ids: GeradorDeId) -> None:
        self._sessoes = sessoes
        self._pacientes = pacientes
        self._leituras = leituras
        self._confirmacoes = confirmacoes
        self._duvidas = duvidas
        self._armazem = armazem
        self._uow = uow
        self._relogio = relogio
        self._ids = ids

    def registrar(self, sessao_id: str, quadros: list[bytes], duracao_s: float) -> dict:
        """Toda suspeita do estágio 1: o recorte fica disponível na hora, com o veredito 'avaliando'."""
        sessao_em_andamento(self._sessoes, sessao_id)
        leitura = self._leituras.ultima(sessao_id) or {}
        duvida = DuvidaDeDor.registrar(
            duvida_id=self._ids.novo(), sessao_id=sessao_id, criado_em=self._relogio.agora(), duracao_s=duracao_s,
            quadros=len(quadros), wong_baker_estimado=leitura.get("wong_baker"), dor_relativa=leitura.get("dor_relativa"))
        self._armazem.guardar(duvida.id, quadros)
        self._duvidas.adicionar(duvida)
        self._uow.commit()
        return self._visao(duvida)

    def registrar_veredito(self, sessao_id: str, duvida_id: str, confirmacao_id: str | None) -> dict:
        """Veredito do estágio 2 (ou a falta dele). Vale mesmo depois de encerrada a consulta: é só auxílio."""
        duvida = self._duvida(duvida_id)
        if duvida.sessao_id != sessao_id:
            raise DuvidaInexistente(duvida_id)
        agora = self._relogio.agora()
        if not confirmacao_id:
            duvida = duvida.sem_resultado(agora)
        else:
            confirmacao = self._confirmacoes.obter(confirmacao_id)
            if confirmacao is None or confirmacao["sessao_id"] != sessao_id:
                raise ValueError("confirmação inexistente nesta consulta")
            duvida = duvida.com_veredito(confirmacao, agora)
        self._duvidas.salvar(duvida)
        self._uow.commit()
        return self._visao(duvida)

    def _visao(self, duvida: DuvidaDeDor) -> dict:
        sessao = self._sessoes.obter(duvida.sessao_id)
        paciente = self._pacientes.obter(sessao.paciente_id) if sessao else None
        return {**duvida.__dict__, "pendente": duvida.pendente, "avaliando": duvida.avaliando,
                "veredito_texto": duvida.veredito_texto, "perto_do_limiar": duvida.perto_do_limiar,
                "categoria_texto": CATEGORIAS.get(duvida.categoria or "", ""),
                "paciente_nome": paciente.nome if paciente else "", "paciente_id": sessao.paciente_id if sessao else ""}

    def listar(self, pendentes: bool | None = True) -> list[dict]:
        return [self._visao(d) for d in self._duvidas.listar(pendentes)]

    def da_sessao(self, sessao_id: str) -> list[dict]:
        """Marcas desta consulta, para o médico ver e classificar sem sair do atendimento."""
        return [self._visao(d) for d in self._duvidas.listar(None) if d.sessao_id == sessao_id]

    def pendentes(self) -> int:
        return len(self._duvidas.listar(True))

    def _duvida(self, duvida_id: str) -> DuvidaDeDor:
        duvida = self._duvidas.obter(duvida_id)
        if duvida is None:
            raise DuvidaInexistente(duvida_id)
        return duvida

    def obter(self, duvida_id: str) -> dict:
        return self._visao(self._duvida(duvida_id))

    def quadro(self, duvida_id: str, indice: int) -> bytes | None:
        duvida = self._duvida(duvida_id)
        if not 0 <= indice < duvida.quadros:
            return None
        return self._armazem.ler(duvida.id, indice)

    def classificar(self, duvida_id: str, face, categoria: str, observacao: str = "") -> dict:
        duvida = self._duvida(duvida_id).classificar(face, categoria, observacao, self._relogio.agora())
        self._duvidas.salvar(duvida)
        self._uow.commit()
        return self._visao(duvida)

    def proxima_pendente(self, depois_de: str | None = None) -> str | None:
        ids = [d.id for d in self._duvidas.listar(True) if d.id != depois_de]
        return ids[-1] if ids else None  # a mais antiga primeiro: fila de revisão
