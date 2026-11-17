"""Fila de alertas do plantão: listar, reconhecer e fechar."""
from __future__ import annotations

from flask import Blueprint, redirect, render_template, request

from application.anomalia.servico import ServicoAnomalia
from application.atendimento.servico_consulta import ServicoConsulta
from application.plantao.servico import ServicoAlertasPlantao
from web.injecao import servico
from web.models.formularios import proximo_de_alertas, status_de_alerta

alertas_bp = Blueprint("alertas", __name__)


ABAS = ("consultas", "internacao", "anomalia")


@alertas_bp.get("/alertas")
def listar():
    """Uma caixa só: dor das consultas, fila da internação e anomalia de padrão."""
    aba = request.args.get("aba") if request.args.get("aba") in ABAS else "consultas"
    status = status_de_alerta(request.args.get("status"))
    if aba == "internacao" and "status" not in request.args:
        status = "open"
    plantao = servico(ServicoAlertasPlantao)
    return render_template(
        "alertas.html", aba=aba, status_filter=status,
        dor=servico(ServicoConsulta).alertas_de_dor_ativos(),
        abertos_internacao=plantao.abertos(),
        alerts=plantao.listar(status) if aba == "internacao" else [],
        anomalias=servico(ServicoAnomalia).alertas() if aba == "anomalia" else [],
    )


@alertas_bp.post("/alertas/<int:alert_id>/ack")
def reconhecer(alert_id: int):
    servico(ServicoAlertasPlantao).reconhecer(alert_id)
    return redirect(proximo_de_alertas(request.form.get("next")))


@alertas_bp.post("/alertas/<int:alert_id>/close")
def fechar(alert_id: int):
    servico(ServicoAlertasPlantao).fechar(alert_id)
    return redirect(proximo_de_alertas(request.form.get("next")))
