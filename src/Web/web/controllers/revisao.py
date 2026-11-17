"""Marcas de atenção da dor: o médico assiste ao recorte, vê o veredito do validador e classifica (ADR-004)."""
from __future__ import annotations

from flask import Blueprint, Response, abort, jsonify, redirect, render_template, request, url_for

from application.atendimento.servico_duvidas import DuvidaInexistente, ServicoDuvidas
from application.atendimento.servico_validacao import ServicoValidacaoDeMarcas
from domain.atendimento.duvida import CATEGORIAS
from domain.atendimento.sessao import SessaoRecusada
from web.injecao import servico
from web.models.formularios import recorte_de_duvida

revisao_bp = Blueprint("revisao", __name__)
FACES = [(0, "😀"), (2, "🙂"), (4, "😐"), (6, "🙁"), (8, "😣"), (10, "😭")]


CAMPOS_DA_CONSULTA = ("id", "criado_em", "duracao_s", "quadros", "pendente", "avaliando", "veredito",
                      "veredito_texto", "categoria_texto", "face_classificada")


@revisao_bp.post("/api/sessoes/<sessao_id>/duvidas")
def api_registrar(sessao_id: str):
    """Marca de atenção: fica disponível na hora; o veredito do estágio 2 vem da fila do servidor."""
    try:
        quadros, duracao, neutro = recorte_de_duvida(request.files, request.form)
        marca = servico(ServicoValidacaoDeMarcas).receber(sessao_id, quadros, duracao, neutro)
        return jsonify({**{k: marca[k] for k in CAMPOS_DA_CONSULTA}, "na_fila": marca["na_fila"]})
    except (SessaoRecusada, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400


@revisao_bp.get("/api/sessoes/<sessao_id>/duvidas")
def api_da_sessao(sessao_id: str):
    return jsonify([{k: d[k] for k in CAMPOS_DA_CONSULTA} for d in servico(ServicoDuvidas).da_sessao(sessao_id)])


@revisao_bp.get("/revisao")
def lista():
    aba = "classificadas" if request.args.get("aba") == "classificadas" else "pendentes"
    duvidas = servico(ServicoDuvidas)
    return render_template("revisao/lista.html", aba=aba, duvidas=duvidas.listar(aba == "pendentes"),
                           total_pendentes=duvidas.pendentes())


@revisao_bp.get("/revisao/<duvida_id>")
def detalhe(duvida_id: str):
    try:
        duvida = servico(ServicoDuvidas).obter(duvida_id)
    except DuvidaInexistente:
        return redirect(url_for("revisao.lista"))
    return render_template("revisao/duvida.html", duvida=duvida, faces=FACES, categorias=CATEGORIAS,
                           erro=request.args.get("erro"))


@revisao_bp.post("/revisao/<duvida_id>")
def classificar(duvida_id: str):
    duvidas = servico(ServicoDuvidas)
    try:
        face = int(request.form.get("face", ""))
        duvidas.classificar(duvida_id, face, request.form.get("categoria") or "", request.form.get("observacao") or "")
    except DuvidaInexistente:
        return redirect(url_for("revisao.lista"))
    except ValueError as exc:
        return redirect(url_for("revisao.detalhe", duvida_id=duvida_id, erro=str(exc) or "classificação inválida"))
    proxima = duvidas.proxima_pendente(depois_de=duvida_id)
    return redirect(url_for("revisao.detalhe", duvida_id=proxima) if proxima else url_for("revisao.lista"))


@revisao_bp.get("/revisao/<duvida_id>/quadros/<int:indice>.jpg")
def quadro(duvida_id: str, indice: int):
    try:
        dados = servico(ServicoDuvidas).quadro(duvida_id, indice)
    except (DuvidaInexistente, ValueError):
        abort(404)
    if dados is None:
        abort(404)
    resposta = Response(dados, mimetype="image/jpeg")
    resposta.headers["Cache-Control"] = "private, no-store"  # imagem de paciente: não fica em cache
    return resposta
