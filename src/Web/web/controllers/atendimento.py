"""Consultório: cadastro, consulta ao vivo (conversa, câmera, cascata de dor) e relatório."""
from __future__ import annotations

import logging
import uuid

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from application.atendimento.portas import (
    AvaliadorIndisponivel,
    EmissorDeTokenDeFala,
    Estagio2Indisponivel,
    ServicoExternoNaoConfigurado,
)
from application.atendimento.servico_cadastro import ServicoCadastro
from application.atendimento.servico_camera import ServicoCamera
from application.atendimento.servico_cascata import ServicoCascataDor
from application.atendimento.servico_consulta import ServicoConsulta
from application.atendimento.servico_conversa import ServicoConversa
from application.plantao.servico import ServicoAlertasPlantao
from application.sistema import ServicoSistema
from domain.atendimento.cascata import SemRostoNosRecortes
from domain.atendimento.paciente import ExclusaoDePacienteRecusada, NomeInvalido, PacienteInexistente
from domain.atendimento.sessao import SessaoRecusada
from web.injecao import servico
from web.models.formularios import blendshapes_validos, recortes_do_formulario

atendimento_bp = Blueprint("atendimento", __name__)
log = logging.getLogger(__name__)


def _erro(mensagem: str, status: int = 400):
    return jsonify({"error": mensagem}), status


# --- cadastro ----------------------------------------------------------------------------------
@atendimento_bp.get("/")
def hoje():
    consulta = servico(ServicoConsulta)
    return render_template("hoje.html", em_andamento=consulta.em_andamento(),
                           alertas_dor=consulta.alertas_de_dor_ativos(),
                           alertas_internacao=servico(ServicoAlertasPlantao).abertos())


def _pacientes(erro=None, status=200, busca=""):
    andamento = {c["paciente_id"]: c["sessao_id"] for c in servico(ServicoConsulta).em_andamento()}
    return render_template("pacientes/lista.html", pacientes=servico(ServicoCadastro).listar(busca),
                           em_andamento=andamento, busca=busca, erro=erro), status


@atendimento_bp.get("/pacientes")
def pacientes():
    return _pacientes(busca=(request.args.get("q") or "").strip())


@atendimento_bp.post("/pacientes")
def pacientes_criar():
    paciente_id = str(uuid.uuid4())
    try:
        servico(ServicoCadastro).cadastrar(paciente_id, request.form.get("nome") or "")
    except NomeInvalido as exc:
        return _pacientes(str(exc), 400)
    return redirect(url_for("atendimento.ficha", paciente_id=paciente_id))


def _ficha(paciente_id: str, erro=None, status=200):
    try:
        ficha_ = servico(ServicoConsulta).ficha(paciente_id)
    except PacienteInexistente:
        return redirect(url_for("atendimento.pacientes"))
    return render_template("pacientes/ficha.html", ficha=ficha_, erro=erro), status


@atendimento_bp.get("/pacientes/<paciente_id>")
def ficha(paciente_id: str):
    return _ficha(paciente_id)


@atendimento_bp.post("/pacientes/<paciente_id>")
def pacientes_corrigir(paciente_id: str):
    try:
        servico(ServicoCadastro).corrigir(paciente_id, request.form.get("nome") or "")
    except NomeInvalido as exc:
        return _ficha(paciente_id, str(exc), 400)
    except PacienteInexistente as exc:
        return _pacientes(str(exc), 400)
    return redirect(url_for("atendimento.ficha", paciente_id=paciente_id))


@atendimento_bp.post("/pacientes/<paciente_id>/excluir")
def pacientes_excluir(paciente_id: str):
    try:
        servico(ServicoCadastro).excluir(paciente_id)
    except ExclusaoDePacienteRecusada:
        return _pacientes("A exclusão de paciente é recusada. O histórico permanece.", 400)
    return redirect(url_for("atendimento.pacientes"))


# --- sessão -------------------------------------------------------------------------------------
@atendimento_bp.post("/sessoes")
def sessoes_criar():
    sessao_id = str(uuid.uuid4())
    try:
        servico(ServicoConsulta).iniciar(sessao_id, (request.form.get("paciente_id") or "").strip())
    except PacienteInexistente:
        return redirect(url_for("atendimento.pacientes"))
    return redirect(url_for("atendimento.preparar", sessao_id=sessao_id))


def _etapa(sessao_id: str, template: str, **extra):
    """Etapas da consulta em andamento; consulta encerrada vai direto ao relatório."""
    try:
        leitura = servico(ServicoConsulta).metrica(sessao_id)
    except SessaoRecusada:
        return redirect(url_for("atendimento.pacientes"))
    if leitura["estado"] != "em_andamento":
        return redirect(url_for("atendimento.consulta_relatorio", sessao_id=sessao_id))
    return render_template(template, leitura=leitura, **extra)


@atendimento_bp.get("/consulta/<sessao_id>/preparar")
def preparar(sessao_id: str):
    return _etapa(sessao_id, "consulta/preparar.html", diagnostico=servico(ServicoSistema).diagnostico())


@atendimento_bp.get("/consulta/<sessao_id>")
def consulta(sessao_id: str):
    return _etapa(sessao_id, "consulta/atender.html")


@atendimento_bp.get("/consulta/<sessao_id>/encerrar")
def encerrar(sessao_id: str):
    try:
        conversa = servico(ServicoConversa).transcricao(sessao_id)
    except SessaoRecusada:
        return redirect(url_for("atendimento.pacientes"))
    return _etapa(sessao_id, "consulta/encerrar.html", conversa=conversa)


@atendimento_bp.get("/api/sessoes/<sessao_id>/metrica")
def api_metrica(sessao_id: str):
    try:
        return jsonify(servico(ServicoConsulta).metrica(sessao_id))
    except SessaoRecusada:
        return _erro("sessao inexistente", 404)


@atendimento_bp.post("/api/sessoes/<sessao_id>/observacao")
def api_observacao(sessao_id: str):
    try:
        return jsonify(servico(ServicoConsulta).registrar_observacao(sessao_id, request.get_json(silent=True) or {}))
    except SessaoRecusada as exc:
        return _erro(str(exc))


@atendimento_bp.post("/sessoes/<sessao_id>/encerrar")
def sessoes_encerrar(sessao_id: str):
    try:
        servico(ServicoConsulta).encerrar_sessao(sessao_id)
    except SessaoRecusada:
        pass
    return redirect(url_for("atendimento.consulta_relatorio", sessao_id=sessao_id))


@atendimento_bp.get("/consulta/<sessao_id>/relatorio")
def consulta_relatorio(sessao_id: str):
    try:
        texto = servico(ServicoConsulta).relatorio(sessao_id)
    except SessaoRecusada:
        return redirect(url_for("atendimento.pacientes"))
    return render_template("consulta/relatorio.html", relatorio=texto,
                           conversa=servico(ServicoConversa).transcricao(sessao_id))


@atendimento_bp.post("/api/alertas-dor/<alerta_id>/ciencia")
def api_ciencia(alerta_id: str):
    try:
        servico(ServicoConsulta).dar_ciencia_dor(alerta_id)
    except SessaoRecusada:
        return _erro("alerta encerrado ou inexistente")
    return jsonify({"ok": True})


@atendimento_bp.post("/api/alertas-dor/<alerta_id>/encerrar")
def api_encerrar_dor(alerta_id: str):
    try:
        servico(ServicoConsulta).encerrar_dor(alerta_id)
    except SessaoRecusada:
        return _erro("alerta encerrado ou inexistente")
    return jsonify({"ok": True})


# --- conversa ao vivo ------------------------------------------------------------------------------
@atendimento_bp.get("/api/azure/speech-token")
def api_speech_token():
    try:
        return jsonify(servico(EmissorDeTokenDeFala).emitir())
    except ServicoExternoNaoConfigurado as exc:
        return jsonify({"error": "azure_nao_configurado", "missing": exc.missing}), 503
    except Exception as exc:  # rede ou Azure fora do ar: a tela mostra o motivo
        log.warning("token do Azure Speech falhou: %s", exc)
        return _erro(f"falha ao obter token do Azure Speech: {exc}", 502)


@atendimento_bp.get("/api/sessoes/<sessao_id>/transcricao")
def api_transcricao(sessao_id: str):
    try:
        return jsonify(servico(ServicoConversa).transcricao(sessao_id))
    except SessaoRecusada:
        return _erro("sessao inexistente", 404)


@atendimento_bp.post("/api/sessoes/<sessao_id>/falas")
def api_fala(sessao_id: str):
    corpo = request.get_json(silent=True) or {}
    locutor = (corpo.get("locutor") or "").strip()
    offset = corpo.get("offset_ms")
    conversa = servico(ServicoConversa)
    try:
        papel = (corpo.get("papel") or "").strip()
        if papel and locutor:
            conversa.definir_papel(sessao_id, locutor, papel)
        return jsonify(conversa.registrar_fala(
            sessao_id, corpo.get("texto") or "", locutor=locutor,
            offset_ms=int(offset) if isinstance(offset, (int, float)) else None,
        ))
    except (SessaoRecusada, ValueError) as exc:
        return _erro(str(exc))


@atendimento_bp.post("/api/sessoes/<sessao_id>/locutores")
def api_locutor(sessao_id: str):
    corpo = request.get_json(silent=True) or {}
    conversa = servico(ServicoConversa)
    try:
        conversa.definir_papel(sessao_id, corpo.get("locutor") or "", corpo.get("papel") or "")
        return jsonify(conversa.transcricao(sessao_id))
    except SessaoRecusada:
        return _erro("sessao inexistente", 404)
    except ValueError as exc:
        return _erro(str(exc))


# --- câmera e cascata de dor (ADR-002) ---------------------------------------------------------------
@atendimento_bp.post("/api/sessoes/<sessao_id>/face")
def api_face(sessao_id: str):
    """Estágio 1: recebe só os blendshapes (números) do rosto, a cada ~1 s."""
    try:
        blendshapes = blendshapes_validos(request.get_json(silent=True) or {})
        return jsonify(servico(ServicoCamera).registrar_leitura(sessao_id, blendshapes))
    except (SessaoRecusada, ValueError) as exc:
        return _erro(str(exc))


@atendimento_bp.post("/api/sessoes/<sessao_id>/face/confirmar")
def api_face_confirmar(sessao_id: str):
    """Estágio 2: recortes JPEG do rosto, só quando o estágio 1 suspeitou de dor; avaliados em memória."""
    cascata = servico(ServicoCascataDor)
    if not cascata.disponivel():
        return _erro("estagio2_indisponivel", 503)
    try:
        suspeitos, neutro = recortes_do_formulario(request.files)
        return jsonify(cascata.confirmar(sessao_id, suspeitos, neutro))
    except (SessaoRecusada, ValueError) as exc:
        return _erro(str(exc))
    except Estagio2Indisponivel:
        return _erro("estagio2_indisponivel", 503)
    except (AvaliadorIndisponivel, SemRostoNosRecortes) as exc:
        log.warning("estágio 2 sem resultado na sessão %s: %s", sessao_id, exc)
        return _erro(str(exc), 422)


@atendimento_bp.post("/api/sessoes/<sessao_id>/autorrelato")
def api_autorrelato(sessao_id: str):
    corpo = request.get_json(silent=True) or {}
    try:
        return jsonify(servico(ServicoCascataDor).registrar_autorrelato(sessao_id, corpo.get("wong_baker")))
    except (SessaoRecusada, ValueError) as exc:
        return _erro(str(exc))
