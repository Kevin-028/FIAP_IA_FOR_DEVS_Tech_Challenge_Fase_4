"""App Flask (MVC) — Tech Challenge Fase 4. Rodar: python -m web.app"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask, request
from injector import Module

from application.atendimento.servico_consulta import ServicoConsulta
from application.atendimento.servico_duvidas import ServicoDuvidas
from application.plantao.servico import ServicoAlertasPlantao
from application.sistema import ServicoSistema
from infrastructure.caminhos import ROOT
from infrastructure.persistencia.conexao import ProvedorDeConexao
from web.controllers.alertas import alertas_bp
from web.controllers.anomalia import anomalia_bp
from web.controllers.atendimento import atendimento_bp
from web.controllers.plantao import plantao_bp
from web.controllers.revisao import revisao_bp
from web.dependencias import criar_injetor
from web.models.apresentacao import data_hora, hora, secao_do_caminho

# uma vez, na importação: create_app não recarrega o .env (os testes removem as chaves do Azure depois disso)
load_dotenv(os.path.join(ROOT, ".env"))

AVISO_EDUCACIONAL = (
    "Demo educacional FIAP. Dados PhysioNet/sintéticos — não usar com paciente real. "
    "Não substitui avaliação médica e não emite prescrição."
)


def create_app(caminho_banco: str | None = None, *modulos_extras: Module) -> Flask:
    app = Flask(__name__, template_folder="views", static_folder="static")
    app.config["RAIZ_PROJETO"] = ROOT
    injetor = criar_injetor(caminho_banco, *modulos_extras)
    app.extensions["injector"] = injetor
    for blueprint in (plantao_bp, atendimento_bp, anomalia_bp, alertas_bp, revisao_bp):
        app.register_blueprint(blueprint)

    @app.teardown_appcontext
    def _fechar_conexao(_erro):
        injetor.get(ProvedorDeConexao).fechar()

    app.add_template_filter(hora, "hora")
    app.add_template_filter(data_hora, "data_hora")

    @app.context_processor
    def _navegacao():
        """Menu: seção ativa, alertas que pedem ação e pendências de configuração."""
        dor = len(injetor.get(ServicoConsulta).alertas_de_dor_ativos())
        return {
            "secao": secao_do_caminho(request.path or ""),
            "alertas_ativos": dor + injetor.get(ServicoAlertasPlantao).abertos(),
            "pendencias_sistema": injetor.get(ServicoSistema).pendencias(),
            "duvidas_pendentes": injetor.get(ServicoDuvidas).pendentes(),
            "edu_disclaimer": AVISO_EDUCACIONAL,
        }

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=True)
