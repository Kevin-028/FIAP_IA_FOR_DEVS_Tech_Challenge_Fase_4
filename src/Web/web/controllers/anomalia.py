"""Anomalia de padrão: treinar no corpus e avaliar uma série. Contrato à parte da consulta."""
from __future__ import annotations

import uuid

from flask import Blueprint, redirect, render_template, request, url_for

from application.anomalia.servico import ServicoAnomalia
from application.sistema import ServicoSistema
from domain.anomalia.modelo import DetectorDeFaixaFixaRecusado, ModeloAusente
from web.injecao import servico

anomalia_bp = Blueprint("anomalia", __name__)


def _pagina(leitura=None, erro=None, status=200):
    return render_template("sistema.html", modelos=servico(ServicoAnomalia).listar_modelos(),
                           diagnostico=servico(ServicoSistema).diagnostico(), leitura=leitura, erro=erro), status


@anomalia_bp.get("/sistema")
def pagina():
    return _pagina()


@anomalia_bp.get("/anomalia")
def pagina_antiga():
    return redirect(url_for("anomalia.pagina"), 301)


@anomalia_bp.post("/anomalia/treinar")
def treinar():
    try:
        servico(ServicoAnomalia).treinar(str(uuid.uuid4()))
    except ModeloAusente as exc:
        return _pagina(erro=str(exc), status=400)
    return redirect(url_for("anomalia.pagina"))


@anomalia_bp.post("/anomalia/avaliar")
def avaliar():
    anomalia = servico(ServicoAnomalia)
    if request.form.get("faixa_fixa"):
        try:
            anomalia.avaliar_faixa_fixa()
        except DetectorDeFaixaFixaRecusado as exc:
            return _pagina(erro=str(exc), status=400)
    serie = (request.form.get("serie_id") or "").strip()
    modelo_id = (request.form.get("modelo_id") or "").strip()
    try:
        leitura = anomalia.avaliar_serie_do_corpus(modelo_id, serie)
    except ModeloAusente as exc:
        return _pagina(erro=str(exc), status=400)
    if leitura is None:
        return _pagina(erro="Série não está no corpus.", status=404)
    return _pagina(leitura=leitura)
