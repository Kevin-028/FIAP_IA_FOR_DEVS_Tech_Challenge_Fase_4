"""Páginas e APIs do plantão multimodal da Fase 4 (vídeo, áudio, anomalias, monitor)."""
from __future__ import annotations

import os
import tempfile
import wave

from flask import Blueprint, current_app, jsonify, redirect, render_template, request

from application.plantao.portas import AudioSemServicoExterno
from application.plantao.servico import ServicoPlantao
from domain.plantao.video_report import OPENPOSE_NOTE
from web.injecao import servico
from web.models.formularios import SIM

plantao_bp = Blueprint("plantao", __name__)
AMOSTRA_WAV = ("hospital_data", "fase4", "samples", "consulta.wav")


def _patient_id(plantao: ServicoPlantao) -> str:
    digitado = (request.values.get("record") or "").strip()
    if digitado:
        return digitado
    return (request.values.get("patient_id") or "").strip() or plantao.paciente_padrao()


def _corpo_patient_id(plantao: ServicoPlantao, corpo: dict) -> str:
    return (corpo.get("patient_id") or request.values.get("patient_id") or plantao.paciente_padrao()).strip()


def _pagina(nome: str, **extra):
    plantao = servico(ServicoPlantao)
    patient_id = _patient_id(plantao)
    erro = plantao.abrir_registro(patient_id)
    return render_template(nome, patients=plantao.pacientes(), patient_id=patient_id, record_error=erro,
                           openpose_note=OPENPOSE_NOTE, **extra)


@plantao_bp.route("/internacao")
def index():
    plantao = servico(ServicoPlantao)
    patient_id = _patient_id(plantao)
    erro = plantao.abrir_registro(patient_id)
    return render_template(
        "internacao/painel.html", patients=plantao.pacientes(), patient_id=patient_id, record_error=erro,
        vital_source=None if erro else plantao.fonte_vital(patient_id),
        vitals_count=plantao.painel(patient_id)["vitals_count"], **plantao.anomalias(patient_id),
    )


@plantao_bp.route("/internacao/exames")
def exames_page():
    return _pagina("internacao/exames.html")


@plantao_bp.route("/internacao/monitor")
def monitor_page():
    return _pagina("internacao/monitor.html")


ANTIGAS = {"": "/internacao", "/anomalias": "/internacao", "/video": "/internacao/exames",
           "/audio": "/internacao/exames", "/monitor": "/internacao/monitor"}


@plantao_bp.route("/fase4", defaults={"resto": ""})
@plantao_bp.route("/fase4/<path:resto>")
def rotas_antigas(resto: str):
    """Endereços da versão anterior continuam valendo."""
    destino = ANTIGAS.get("/" + resto if resto else "", "/internacao")
    consulta = request.query_string.decode()
    return redirect(destino + ("?" + consulta if consulta else ""), 301)


def _com_arquivo_temporario(upload, sufixo: str, acao):
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=sufixo)
    temp.close()
    try:
        upload.save(temp.name)
        return acao(temp.name)
    finally:
        if os.path.isfile(temp.name):
            os.remove(temp.name)


@plantao_bp.route("/api/fase4/video/arquivo", methods=["POST"])
def api_video():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify({"error": "envie um arquivo de video"}), 400
    plantao = servico(ServicoPlantao)
    patient_id = _patient_id(plantao)
    sufixo = os.path.splitext(upload.filename)[1] or ".mp4"
    return jsonify(_com_arquivo_temporario(upload, sufixo, lambda caminho: plantao.processar_video(caminho, patient_id)))


def _audio(plantao: ServicoPlantao, caminho: str, patient_id: str):
    try:
        return jsonify(plantao.processar_audio(caminho, patient_id))
    except AudioSemServicoExterno as exc:
        return jsonify({"error": "azure_nao_configurado", "missing": exc.missing, "vocal": exc.vocal}), 503


@plantao_bp.route("/api/fase4/audio", methods=["POST"])
def api_audio():
    plantao = servico(ServicoPlantao)
    patient_id = _patient_id(plantao)
    if (request.values.get("use_sample") or "").strip() in SIM:
        amostra = os.path.join(current_app.config["RAIZ_PROJETO"], *AMOSTRA_WAV)
        if not os.path.isfile(amostra):
            return jsonify({"error": "amostra ausente; rode python scripts/make_demo_audio.py"}), 404
        return _audio(plantao, amostra, patient_id)
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify({"error": "envie um WAV 16 kHz mono"}), 400

    def _processar(caminho):
        try:
            return _audio(plantao, caminho, patient_id)
        except (wave.Error, ValueError) as exc:  # WAV inválido ou não PCM 16-bit
            return jsonify({"error": str(exc)}), 400

    return _com_arquivo_temporario(upload, ".wav", _processar)


@plantao_bp.route("/api/fase4/anomalias/alertas", methods=["POST"])
def api_anomalias_alertas():
    plantao = servico(ServicoPlantao)
    patient_id = _corpo_patient_id(plantao, request.get_json(silent=True) or {})
    erro = plantao.abrir_registro(patient_id)
    if erro:
        return jsonify({"error": erro}), 404
    resultado = plantao.alertas_da_fusao(patient_id)
    return jsonify({"patient_id": patient_id, **resultado, "prescribes": False})


@plantao_bp.route("/api/fase4/monitor/serie")
def api_serie():
    plantao = servico(ServicoPlantao)
    return jsonify(plantao.serie(_patient_id(plantao)))


@plantao_bp.route("/api/fase4/monitor/reset", methods=["POST"])
def api_reset():
    plantao = servico(ServicoPlantao)
    patient_id = _corpo_patient_id(plantao, request.get_json(silent=True) or {})
    plantao.resetar_monitor(patient_id)
    return jsonify({"ok": True, "patient_id": patient_id})


@plantao_bp.route("/api/fase4/monitor/tick", methods=["POST"])
def api_tick():
    plantao = servico(ServicoPlantao)
    corpo = request.get_json(silent=True) or {}
    out = plantao.tick(_corpo_patient_id(plantao, corpo), vital=corpo.get("vital"), movement=corpo.get("movement"))
    return jsonify({"level": out["level"], "new_alerts": out["new_alerts"], "avaliacao": out["avaliacao"],
                    "prescribes": False})
