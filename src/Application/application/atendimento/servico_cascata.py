"""Estágio 2 da cascata de dor (ADR-002): confirmar com recortes do rosto e registrar o autorrelato Wong-Baker.

Os recortes ficam em memória durante a avaliação; só números são gravados.
"""
from __future__ import annotations

from application.atendimento.portas import Estagio2, Estagio2Indisponivel
from application.atendimento.servico_camera import ServicoCamera, alerta_face_ativo
from application.atendimento.servico_consulta import sessao_em_andamento
from application.portas import GeradorDeId, Relogio, UnidadeDeTrabalho
from domain.atendimento import cascata
from domain.atendimento.dor_facial import DESCRICAO_WONG_BAKER
from domain.atendimento.repositorios import (
    RepositorioAlertaDor,
    RepositorioAutorrelato,
    RepositorioConfirmacaoDor,
    RepositorioLeituraFace,
    RepositorioSessao,
)


class ServicoCascataDor:
    def __init__(
        self,
        sessoes: RepositorioSessao,
        leituras: RepositorioLeituraFace,
        confirmacoes: RepositorioConfirmacaoDor,
        autorrelatos: RepositorioAutorrelato,
        alertas: RepositorioAlertaDor,
        camera: ServicoCamera,
        estagio2: Estagio2,
        uow: UnidadeDeTrabalho,
        relogio: Relogio,
        ids: GeradorDeId,
    ) -> None:
        self._sessoes = sessoes
        self._leituras = leituras
        self._confirmacoes = confirmacoes
        self._autorrelatos = autorrelatos
        self._alertas = alertas
        self._camera = camera
        self._estagio2 = estagio2
        self._uow = uow
        self._relogio = relogio
        self._ids = ids

    def disponivel(self) -> bool:
        return self._estagio2.disponivel()

    def confirmar(self, sessao_id: str, suspeitos: list[bytes], neutro: bytes | None = None, *,
                  exigir_em_andamento: bool = True) -> dict:
        """exigir_em_andamento=False: a fila do validador ainda avalia marcas de uma consulta que já encerrou."""
        if not self._estagio2.disponivel():
            raise Estagio2Indisponivel("estagio2_indisponivel")
        if not suspeitos:
            raise ValueError("nenhum recorte suspeito")
        self._sessao(sessao_id, exigir_em_andamento)
        resultados = self._estagio2.avaliar(([neutro] if neutro else []) + list(suspeitos))
        aus_neutro = resultados.pop(0) if neutro else None
        resultado = cascata.avaliar_confirmacao(self._estagio2.nome, resultados, aus_neutro)
        return self.registrar_confirmacao(sessao_id, resultado, exigir_em_andamento=exigir_em_andamento)

    def _sessao(self, sessao_id: str, exigir_em_andamento: bool):
        if exigir_em_andamento:
            return sessao_em_andamento(self._sessoes, sessao_id)
        sessao = self._sessoes.obter(sessao_id)
        if sessao is None:
            raise ValueError("consulta inexistente")
        return sessao

    def registrar_confirmacao(self, sessao_id: str, resultado: dict, *, registrado_em: str | None = None,
                              exigir_em_andamento: bool = True) -> dict:
        sessao = self._sessao(sessao_id, exigir_em_andamento)
        face = cascata.face_wong_baker(resultado.get("wong_baker"))
        quando = registrado_em or self._relogio.agora()
        confirmacao = {
            "id": self._ids.novo(),
            "registrado_em": quando,
            "detector": str(resultado["detector"]),
            "pspi": float(resultado["pspi"]),
            "pspi_base": float(resultado["pspi_base"]),
            "dor_relativa": float(resultado["dor_relativa"]),
            "wong_baker": face,
            "confirmado": bool(resultado["confirmado"]),
            "faces_avaliadas": int(resultado["faces_avaliadas"]),
        }
        self._confirmacoes.adicionar(sessao_id, confirmacao)
        eventos, alerta = [], False
        # consulta encerrada: o veredito fica registrado, mas não abre alerta novo
        if confirmacao["confirmado"] and sessao.em_andamento and not alerta_face_ativo(self._alertas, sessao_id):
            eventos.append(self._camera.abrir_alerta_face(
                sessao_id, quando, cascata.descricao_alerta_confirmado(confirmacao), "dor/desconforto",
                f"Dor no rosto confirmada (Wong-Baker {face})"))
            alerta = True
        self._uow.commit()
        return {"confirmacao": confirmacao, "alerta_dor": alerta, "eventos_novos": eventos}

    def _estimativa(self, sessao_id: str, quando: str) -> tuple[int | None, str | None]:
        ultima = self._confirmacoes.ultima(sessao_id)
        if ultima is not None and cascata.confirmacao_vale_como_estimativa(ultima["registrado_em"], quando):
            return ultima["wong_baker"], "estagio2"
        leitura = self._leituras.ultima(sessao_id)
        return (leitura["wong_baker"], "estagio1") if leitura is not None else (None, None)

    def registrar_autorrelato(self, sessao_id: str, face, *, registrado_em: str | None = None) -> dict:
        """Face apontada pelo paciente, guardada ao lado da estimativa da câmera para medir a concordância."""
        sessao_em_andamento(self._sessoes, sessao_id)
        face = cascata.face_wong_baker(face)
        quando = registrado_em or self._relogio.agora()
        estimado, origem = self._estimativa(sessao_id, quando)
        relato = {"id": self._ids.novo(), "registrado_em": quando, "wong_baker": face,
                  "descricao": DESCRICAO_WONG_BAKER[face], "estimado": estimado, "origem_estimativa": origem}
        self._autorrelatos.adicionar(sessao_id, relato)
        self._uow.commit()
        return relato
