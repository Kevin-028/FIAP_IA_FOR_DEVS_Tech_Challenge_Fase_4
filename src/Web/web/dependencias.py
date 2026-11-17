"""Composition root: o único lugar que conhece as classes concretas da Infrastructure.

Dois módulos do `injector`:
  ModuloInfraestrutura  porta (Protocol) -> adaptador concreto (SQLite, Py-Feat, Azure, scikit-learn...)
  ModuloAplicacao       como montar cada serviço da Application a partir das portas

Para trocar uma implementação (ex.: outro detector de dor), mude só a linha do bind aqui.
Domain e Application não importam o injector: os construtores continuam sendo Python puro.
"""
from __future__ import annotations

from injector import Binder, Injector, InstanceProvider, Module, provider, singleton

from application.anomalia.portas import CorpusVital, MotorDeAnomalia
from application.anomalia.servico import ServicoAnomalia
from application.atendimento.portas import AnalisadorDeTexto, ArmazemDeQuadros, EmissorDeTokenDeFala, Estagio2
from application.atendimento.servico_cadastro import ServicoCadastro
from application.atendimento.servico_camera import ServicoCamera
from application.atendimento.servico_cascata import ServicoCascataDor
from application.atendimento.servico_consulta import ServicoConsulta
from application.atendimento.servico_conversa import ServicoConversa
from application.atendimento.servico_duvidas import ServicoDuvidas
from application.atendimento.servico_validacao import ServicoValidacaoDeMarcas
from application.plantao.portas import (
    AnalisadorDeTextoPlantao,
    AnalisadorDeVideo,
    AnalisadorDeVoz,
    DetectorDeOutliers,
    FonteDeSeries,
    Transcritor,
)
from application.plantao.servico import ServicoAlertasPlantao, ServicoPlantao
from application.portas import FilaDeTrabalho, GeradorDeId, Relogio, UnidadeDeTrabalho
from application.sistema import InventarioDeModelos, ServicoSistema
from domain.anomalia.repositorios import RepositorioAlertaAnomalia, RepositorioModelo
from domain.atendimento import repositorios as rep_atendimento
from domain.plantao.repositorios import RepositorioAlertaPlantao, RepositorioPlantao
from infrastructure.azure.language import AnalisadorAzure
from infrastructure.azure.speech import EmissorDeTokenAzure, TranscritorAzure
from infrastructure.caminhos import ROOT
from infrastructure.fila import FilaEmSegundoPlano
from infrastructure.ia.inventario import InventarioLocal
from infrastructure.ia.isolation_forest import MotorIsolationForest
from infrastructure.ia.outliers import DetectorIsolationForest
from infrastructure.ia.pyfeat import AvaliadorPyFeat
from infrastructure.ia.video_opencv import AnalisadorDeVideoOpenCV
from infrastructure.ia.voz import AnalisadorDeVozNumpy
from infrastructure.persistencia import repositorios_atendimento as sql_atendimento
from infrastructure.persistencia.armazem_quadros import ArmazemDeQuadrosEmDisco
from infrastructure.persistencia.conexao import ProvedorDeConexao, UnidadeDeTrabalhoSqlite
from infrastructure.persistencia.repositorios_anomalia import RepositorioAlertaAnomaliaSqlite, RepositorioModeloSqlite
from infrastructure.persistencia.repositorios_plantao import RepositorioAlertaPlantaoSqlite, RepositorioPlantaoSqlite
from infrastructure.physionet.challenge2019 import FonteChallenge2019
from infrastructure.physionet.corpus import CorpusChallenge2019
from infrastructure.sistema import GeradorUuid, RelogioUtc

# porta do repositório -> classe SQLite que recebe só o ProvedorDeConexao
_REPOSITORIOS = {
    rep_atendimento.RepositorioPaciente: sql_atendimento.RepositorioPacienteSqlite,
    rep_atendimento.RepositorioSessao: sql_atendimento.RepositorioSessaoSqlite,
    rep_atendimento.RepositorioAlertaDor: sql_atendimento.RepositorioAlertaDorSqlite,
    rep_atendimento.RepositorioLeituraFace: sql_atendimento.RepositorioLeituraFaceSqlite,
    rep_atendimento.RepositorioEventoFace: sql_atendimento.RepositorioEventoFaceSqlite,
    rep_atendimento.RepositorioConfirmacaoDor: sql_atendimento.RepositorioConfirmacaoDorSqlite,
    rep_atendimento.RepositorioAutorrelato: sql_atendimento.RepositorioAutorrelatoSqlite,
    rep_atendimento.RepositorioConversa: sql_atendimento.RepositorioConversaSqlite,
    rep_atendimento.RepositorioDuvida: sql_atendimento.RepositorioDuvidaSqlite,
    RepositorioModelo: RepositorioModeloSqlite,
    RepositorioAlertaAnomalia: RepositorioAlertaAnomaliaSqlite,
    RepositorioPlantao: RepositorioPlantaoSqlite,
    RepositorioAlertaPlantao: RepositorioAlertaPlantaoSqlite,
}

# porta sem dependência -> adaptador
_ADAPTADORES = {
    Relogio: RelogioUtc,
    GeradorDeId: GeradorUuid,
    Estagio2: AvaliadorPyFeat,
    AnalisadorDeTexto: AnalisadorAzure,
    AnalisadorDeTextoPlantao: AnalisadorAzure,
    EmissorDeTokenDeFala: EmissorDeTokenAzure,
    Transcritor: TranscritorAzure,
    AnalisadorDeVoz: AnalisadorDeVozNumpy,
    AnalisadorDeVideo: AnalisadorDeVideoOpenCV,
    DetectorDeOutliers: DetectorIsolationForest,
    FonteDeSeries: FonteChallenge2019,
    MotorDeAnomalia: MotorIsolationForest,
    InventarioDeModelos: InventarioLocal,
    ArmazemDeQuadros: ArmazemDeQuadrosEmDisco,
}


class ModuloInfraestrutura(Module):
    def __init__(self, caminho_banco: str | None = None, raiz: str = ROOT) -> None:
        self._caminho_banco = caminho_banco
        self._raiz = raiz

    def configure(self, binder: Binder) -> None:
        # InstanceProvider: as portas são Protocols, e o injector não checa isinstance contra Protocol
        conexao = ProvedorDeConexao(self._caminho_banco)
        binder.bind(ProvedorDeConexao, to=InstanceProvider(conexao))
        binder.bind(UnidadeDeTrabalho, to=InstanceProvider(UnidadeDeTrabalhoSqlite(conexao)))
        for porta, classe in _REPOSITORIOS.items():
            binder.bind(porta, to=InstanceProvider(classe(conexao)))
        for porta, classe in _ADAPTADORES.items():
            binder.bind(porta, to=InstanceProvider(classe()))
        binder.bind(CorpusVital, to=InstanceProvider(CorpusChallenge2019(self._raiz)))
        # validador da dor: uma avaliação por vez, fora da requisição, com conexão própria
        binder.bind(FilaDeTrabalho, to=InstanceProvider(FilaEmSegundoPlano(conexao)))


class ModuloAplicacao(Module):
    """Cada serviço é montado à mão: os parâmetros vêm do injector pelos type hints."""

    @singleton
    @provider
    def cadastro(self, pacientes: rep_atendimento.RepositorioPaciente, uow: UnidadeDeTrabalho) -> ServicoCadastro:
        return ServicoCadastro(pacientes, uow)

    @singleton
    @provider
    def consulta(self, pacientes: rep_atendimento.RepositorioPaciente, sessoes: rep_atendimento.RepositorioSessao,
                 alertas: rep_atendimento.RepositorioAlertaDor, uow: UnidadeDeTrabalho, relogio: Relogio,
                 ids: GeradorDeId) -> ServicoConsulta:
        return ServicoConsulta(pacientes, sessoes, alertas, uow, relogio, ids)

    @singleton
    @provider
    def camera(self, sessoes: rep_atendimento.RepositorioSessao, leituras: rep_atendimento.RepositorioLeituraFace,
               eventos: rep_atendimento.RepositorioEventoFace, confirmacoes: rep_atendimento.RepositorioConfirmacaoDor,
               alertas: rep_atendimento.RepositorioAlertaDor, estagio2: Estagio2, uow: UnidadeDeTrabalho,
               relogio: Relogio, ids: GeradorDeId) -> ServicoCamera:
        return ServicoCamera(sessoes, leituras, eventos, confirmacoes, alertas, estagio2, uow, relogio, ids)

    @singleton
    @provider
    def cascata(self, sessoes: rep_atendimento.RepositorioSessao, leituras: rep_atendimento.RepositorioLeituraFace,
                confirmacoes: rep_atendimento.RepositorioConfirmacaoDor,
                autorrelatos: rep_atendimento.RepositorioAutorrelato, alertas: rep_atendimento.RepositorioAlertaDor,
                camera: ServicoCamera, estagio2: Estagio2, uow: UnidadeDeTrabalho, relogio: Relogio,
                ids: GeradorDeId) -> ServicoCascataDor:
        return ServicoCascataDor(sessoes, leituras, confirmacoes, autorrelatos, alertas, camera, estagio2, uow,
                                 relogio, ids)

    @singleton
    @provider
    def conversa(self, sessoes: rep_atendimento.RepositorioSessao, conversa: rep_atendimento.RepositorioConversa,
                 alertas: rep_atendimento.RepositorioAlertaDor, camera: ServicoCamera, analisador: AnalisadorDeTexto,
                 uow: UnidadeDeTrabalho, relogio: Relogio, ids: GeradorDeId) -> ServicoConversa:
        return ServicoConversa(sessoes, conversa, alertas, camera, analisador, uow, relogio, ids)

    @singleton
    @provider
    def anomalia(self, modelos: RepositorioModelo, alertas: RepositorioAlertaAnomalia, motor: MotorDeAnomalia,
                 corpus: CorpusVital, uow: UnidadeDeTrabalho, relogio: Relogio, ids: GeradorDeId) -> ServicoAnomalia:
        return ServicoAnomalia(modelos, alertas, motor, corpus, uow, relogio, ids)

    @singleton
    @provider
    def plantao(self, plantao: RepositorioPlantao, alertas: RepositorioAlertaPlantao, fonte: FonteDeSeries,
                outliers: DetectorDeOutliers, transcritor: Transcritor, analisador: AnalisadorDeTextoPlantao,
                voz: AnalisadorDeVoz, video: AnalisadorDeVideo, uow: UnidadeDeTrabalho) -> ServicoPlantao:
        return ServicoPlantao(plantao, alertas, fonte, outliers, transcritor, analisador, voz, video, uow)

    @singleton
    @provider
    def alertas_plantao(self, alertas: RepositorioAlertaPlantao, uow: UnidadeDeTrabalho,
                        relogio: Relogio) -> ServicoAlertasPlantao:
        return ServicoAlertasPlantao(alertas, uow, relogio)


class ModuloDuvidas(Module):
    @singleton
    @provider
    def duvidas(self, sessoes: rep_atendimento.RepositorioSessao, pacientes: rep_atendimento.RepositorioPaciente,
                leituras: rep_atendimento.RepositorioLeituraFace,
                confirmacoes: rep_atendimento.RepositorioConfirmacaoDor, duvidas: rep_atendimento.RepositorioDuvida,
                armazem: ArmazemDeQuadros, uow: UnidadeDeTrabalho, relogio: Relogio, ids: GeradorDeId) -> ServicoDuvidas:
        return ServicoDuvidas(sessoes, pacientes, leituras, confirmacoes, duvidas, armazem, uow, relogio, ids)

    @singleton
    @provider
    def validacao(self, duvidas: ServicoDuvidas, cascata: ServicoCascataDor,
                  fila: FilaDeTrabalho) -> ServicoValidacaoDeMarcas:
        return ServicoValidacaoDeMarcas(duvidas, cascata, fila)


class ModuloSistema(Module):
    @singleton
    @provider
    def sistema(self, fala: Transcritor, linguagem: AnalisadorDeTextoPlantao, estagio2: Estagio2,
                inventario: InventarioDeModelos) -> ServicoSistema:
        return ServicoSistema(fala, linguagem, estagio2, inventario)


def criar_injetor(caminho_banco: str | None = None, *modulos_extras: Module) -> Injector:
    """modulos_extras sobrepõem bindings (ex.: testes trocando o Estagio2 por um falso)."""
    return Injector([ModuloInfraestrutura(caminho_banco), ModuloAplicacao(), ModuloSistema(), ModuloDuvidas(), *modulos_extras])
