"""Páginas e APIs da Fase 4."""
from __future__ import annotations

import os
import sys
import tempfile
import wave

import numpy as np
from flask import Blueprint, jsonify, render_template, request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from hospital.db import (
    connect,
    get_patient,
    init_db,
    list_alerts,
    list_movement,
    list_prescriptions,
    list_vitals,
    modality_report_kinds,
    open_alert_count,
    save_modality_report,
)
from multimodal.audio_pipeline import audio_report
from multimodal.azure_language import analyze_text, missing_language
from multimodal.azure_speech import AzureNotConfigured, missing_speech, transcribe_wav
from multimodal.detect_yolo import detections_of
from multimodal.fusion import fuse
from multimodal.monitor import reset_monitor, tick
from multimodal.movement import movement_anomalies
from multimodal.pose_mediapipe import landmarks_of
from multimodal.prescriptions import prescription_anomalies
from multimodal.publish import publish
from multimodal.video_file import analyze_video_file
from multimodal.video_report import OPENPOSE_NOTE
from multimodal.challenge2019 import default_patient, series_of
from multimodal.vitals import vital_anomalies
from multimodal.vocal import vocal_features

fase4_bp = Blueprint("fase4", __name__)


def _db():
    conn = connect()
    init_db(conn)
    return conn


def _patient_id() -> str:
    typed = (request.values.get("record") or "").strip()
    if typed:
        return typed
    return (request.values.get("patient_id") or default_patient()).strip() or default_patient()


def _challenge_patients(conn):
    rows = conn.execute(
        """
        SELECT * FROM patients
         WHERE notes LIKE 'PhysioNet Challenge 2019%'
         ORDER BY id
        """
    ).fetchall()
    return [dict(row) for row in rows]


SAMPLE_WAV = os.path.join(ROOT, "hospital_data", "fase4", "samples", "consulta.wav")


def _open_record(conn, patient_id: str) -> str | None:
    item = series_of(patient_id)
    if item is None:
        return "Registro não encontrado na base do Challenge 2019."
    from hospital.seed_fase4 import store_patient

    needs = (
        get_patient(conn, item["record"]) is None
        or not list_vitals(conn, item["record"])
        or not list_prescriptions(conn, item["record"])
    )
    if needs:
        store_patient(conn, item)
    return None


def _chart(conn, patient_id: str) -> str:
    patient = get_patient(conn, patient_id) or {}
    return " ".join(
        part for part in (patient.get("diagnosis"), patient.get("notes")) if part
    )


def _wav_samples(path: str):
    with wave.open(path, "rb") as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        rate = handle.getframerate()
        raw = handle.readframes(handle.getnframes())
    if width != 2:
        raise ValueError("O WAV precisa ser PCM 16-bit.")
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, rate


def _fuse_plantao(conn, patient_id: str, *, video=None, audio=None):
    return fuse(
        video=video,
        audio=audio,
        vitals=vital_anomalies(list_vitals(conn, patient_id)),
        prescriptions=prescription_anomalies(list_prescriptions(conn, patient_id)),
        movement=movement_anomalies(list_movement(conn, patient_id)),
        chart_text=_chart(conn, patient_id),
    )


def _page(name, **extra):
    conn = _db()
    try:
        patient_id = extra.pop("patient_id", _patient_id())
        missing = _open_record(conn, patient_id)
        return render_template(
            name,
            patients=_challenge_patients(conn),
            patient_id=patient_id,
            record_error=missing,
            openpose_note=OPENPOSE_NOTE,
            **extra,
        )
    finally:
        conn.close()


def _vital_source(patient_id: str) -> str | None:
    item = series_of(patient_id)
    if item is None:
        return None
    return item["notes"]


def _process_audio_path(path: str, patient_id: str):
    samples, rate = _wav_samples(path)
    vocal = vocal_features(samples, rate)
    missing = missing_speech() + missing_language()
    if missing:
        return None, {
            "error": "azure_nao_configurado",
            "missing": missing,
            "vocal": vocal,
        }, 503
    try:
        report = audio_report(
            path,
            transcribe=transcribe_wav,
            analyze=analyze_text,
            samples=samples,
            sample_rate=rate,
        )
    except AzureNotConfigured as exc:
        return None, {
            "error": "azure_nao_configurado",
            "missing": exc.missing,
            "vocal": vocal,
        }, 503
    conn = _db()
    try:
        _open_record(conn, patient_id)
        result = _fuse_plantao(conn, patient_id, audio=report)
        created = publish(conn, patient_id, result)
        save_modality_report(conn, patient_id, "audio", report)
    finally:
        conn.close()
    return {"report": report, "new_alerts": created, "prescribes": False}, None, 200


@fase4_bp.route("/fase4")
def index():
    conn = _db()
    try:
        patient_id = _patient_id()
        missing = _open_record(conn, patient_id)
        vitals = vital_anomalies(list_vitals(conn, patient_id))
        prescriptions = prescription_anomalies(list_prescriptions(conn, patient_id))
        movement = movement_anomalies(list_movement(conn, patient_id))
        kinds = modality_report_kinds(conn, patient_id)
        open_for_patient = sum(
            1 for row in list_alerts(conn, "open") if row.get("patient_id") == patient_id
        )
        return render_template(
            "fase4/index.html",
            patients=_challenge_patients(conn),
            patient_id=patient_id,
            record_error=missing,
            vital_source=None if missing else _vital_source(patient_id),
            vitals_count=len(list_vitals(conn, patient_id)),
            vitals_hits=len(vitals),
            rx_hits=len(prescriptions),
            move_hits=len(movement),
            done_video="video" in kinds,
            done_audio="audio" in kinds,
            open_alerts_patient=open_for_patient,
            open_alerts_total=open_alert_count(conn),
            openpose_note=OPENPOSE_NOTE,
        )
    finally:
        conn.close()


@fase4_bp.route("/fase4/video")
def video_page():
    return _page("fase4/video.html")


@fase4_bp.route("/fase4/audio")
def audio_page():
    return _page("fase4/audio.html")


@fase4_bp.route("/fase4/anomalias")
def anomalias_page():
    conn = _db()
    try:
        patient_id = _patient_id()
        missing = _open_record(conn, patient_id)
        return render_template(
            "fase4/anomalias.html",
            patients=_challenge_patients(conn),
            patient_id=patient_id,
            record_error=missing,
            vital_source=None if missing else _vital_source(patient_id),
            vitals=vital_anomalies(list_vitals(conn, patient_id)),
            prescriptions=prescription_anomalies(list_prescriptions(conn, patient_id)),
            movement=movement_anomalies(list_movement(conn, patient_id)),
        )
    finally:
        conn.close()


@fase4_bp.route("/fase4/monitor")
def monitor_page():
    return _page("fase4/monitor.html")


@fase4_bp.route("/api/fase4/video/arquivo", methods=["POST"])
def api_video():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify({"error": "envie um arquivo de video"}), 400
    patient_id = _patient_id()
    suffix = os.path.splitext(upload.filename)[1] or ".mp4"
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp.close()
    warning = None

    def _detect(frame):
        nonlocal warning
        try:
            return detections_of(frame)
        except FileNotFoundError as exc:
            warning = str(exc)
            return []

    try:
        upload.save(temp.name)
        report = analyze_video_file(temp.name, pose_fn=landmarks_of, detect_fn=_detect)
    finally:
        if os.path.isfile(temp.name):
            os.remove(temp.name)
    conn = _db()
    try:
        _open_record(conn, patient_id)
        result = _fuse_plantao(conn, patient_id, video=report)
        created = publish(conn, patient_id, result)
        save_modality_report(conn, patient_id, "video", report)
    finally:
        conn.close()
    return jsonify({"report": report, "new_alerts": created, "warning": warning, "prescribes": False})


@fase4_bp.route("/api/fase4/audio", methods=["POST"])
def api_audio():
    patient_id = _patient_id()
    if (request.values.get("use_sample") or "").strip() in ("1", "true", "yes"):
        if not os.path.isfile(SAMPLE_WAV):
            return jsonify({"error": "amostra ausente; rode python scripts/make_demo_audio.py"}), 404
        payload, err, status = _process_audio_path(SAMPLE_WAV, patient_id)
        if err:
            return jsonify(err), status
        return jsonify(payload)
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify({"error": "envie um WAV 16 kHz mono"}), 400
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp.close()
    try:
        upload.save(temp.name)
        try:
            payload, err, status = _process_audio_path(temp.name, patient_id)
        except (wave.Error, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400
    finally:
        if os.path.isfile(temp.name):
            os.remove(temp.name)
    if err:
        return jsonify(err), status
    return jsonify(payload)


@fase4_bp.route("/api/fase4/anomalias/alertas", methods=["POST"])
def api_anomalias_alertas():
    body = request.get_json(silent=True) or {}
    patient_id = (body.get("patient_id") or default_patient()).strip()
    conn = _db()
    try:
        missing = _open_record(conn, patient_id)
        if missing:
            return jsonify({"error": missing}), 404
        result = _fuse_plantao(conn, patient_id)
        created = publish(conn, patient_id, result)
    finally:
        conn.close()
    return jsonify({
        "patient_id": patient_id,
        "level": result["level"],
        "new_alerts": created,
        "prescribes": False,
    })


@fase4_bp.route("/api/fase4/monitor/serie")
def api_serie():
    conn = _db()
    try:
        patient_id = _patient_id()
        return jsonify({
            "patient_id": patient_id,
            "vitals": list_vitals(conn, patient_id),
            "movement": list_movement(conn, patient_id),
        })
    finally:
        conn.close()


@fase4_bp.route("/api/fase4/monitor/reset", methods=["POST"])
def api_reset():
    body = request.get_json(silent=True) or {}
    patient_id = (body.get("patient_id") or request.values.get("patient_id") or default_patient()).strip()
    conn = _db()
    try:
        reset_monitor(conn, patient_id)
    finally:
        conn.close()
    return jsonify({"ok": True, "patient_id": patient_id})


@fase4_bp.route("/api/fase4/monitor/tick", methods=["POST"])
def api_tick():
    body = request.get_json(silent=True) or {}
    patient_id = (body.get("patient_id") or default_patient()).strip()
    conn = _db()
    try:
        out = tick(
            conn,
            patient_id,
            vital=body.get("vital"),
            movement=body.get("movement"),
            chart_text=_chart(conn, patient_id),
        )
    finally:
        conn.close()
    return jsonify({"level": out["level"], "new_alerts": out["new_alerts"], "prescribes": False})
