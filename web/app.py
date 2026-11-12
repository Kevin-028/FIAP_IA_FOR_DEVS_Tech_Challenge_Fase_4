"""App Flask — Tech Challenge Fase 4 (plantão multimodal)."""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.dirname(os.path.abspath(__file__))
for path in (ROOT, WEB):
    if path not in sys.path:
        sys.path.insert(0, path)

load_dotenv(os.path.join(ROOT, ".env"))

from controllers.fase4_controller import fase4_bp  # noqa: E402
from hospital.db import (  # noqa: E402
    ack_alert,
    close_alert,
    connect,
    init_db,
    list_alerts,
    open_alert_count,
)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.register_blueprint(fase4_bp)

_VALID_STATUS = {"open", "acked", "closed"}


@app.context_processor
def inject_nav():
    path = ""
    try:
        path = request.path or ""
    except RuntimeError:
        pass
    conn = connect()
    try:
        init_db(conn)
        open_count = open_alert_count(conn)
    finally:
        conn.close()
    return {
        "nav_multimodal": path.rstrip("/") == "/fase4" or path == "/",
        "nav_video": path.startswith("/fase4/video"),
        "nav_audio": path.startswith("/fase4/audio"),
        "nav_anomalias": path.startswith("/fase4/anomalias"),
        "nav_monitor": path.startswith("/fase4/monitor"),
        "nav_alertas": path.startswith("/alertas"),
        "open_alert_count": open_count,
        "edu_disclaimer": (
            "Demo educacional FIAP. Dados PhysioNet/sintéticos — não usar com paciente real. "
            "Não substitui avaliação médica e não emite prescrição."
        ),
    }


@app.get("/")
def home():
    return redirect(url_for("fase4.index"))


@app.get("/alertas")
def alertas():
    status = (request.args.get("status") or "").strip()
    if status and status not in _VALID_STATUS:
        status = ""
    conn = connect()
    try:
        init_db(conn)
        alerts = list_alerts(conn, status or None)
    finally:
        conn.close()
    return render_template("alertas.html", alerts=alerts, status_filter=status or None)


def _alert_next():
    nxt = (request.form.get("next") or "/alertas").strip()
    if not nxt.startswith("/alertas"):
        return "/alertas"
    return nxt


@app.post("/alertas/<int:alert_id>/ack")
def alertas_ack(alert_id: int):
    conn = connect()
    try:
        init_db(conn)
        ack_alert(conn, alert_id)
    finally:
        conn.close()
    return redirect(_alert_next())


@app.post("/alertas/<int:alert_id>/close")
def alertas_close(alert_id: int):
    conn = connect()
    try:
        init_db(conn)
        close_alert(conn, alert_id)
    finally:
        conn.close()
    return redirect(_alert_next())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
