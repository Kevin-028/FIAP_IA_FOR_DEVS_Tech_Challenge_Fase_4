"""Conversa ao vivo: cada fala vira linha, o papel do locutor é deduzido e os pontos de atenção são marcados."""
from __future__ import annotations

import logging

from application.atendimento.portas import AnalisadorDeTexto
from application.atendimento.servico_camera import ServicoCamera
from application.atendimento.servico_consulta import obter_sessao, sessao_em_andamento
from application.portas import GeradorDeId, Relogio, UnidadeDeTrabalho
from domain.atendimento.alerta_dor import AlertaDeDor
from domain.atendimento.conversa import resumo as regras
from domain.atendimento.conversa.atencao import pontos_por_azure, pontos_por_regra
from domain.atendimento.conversa.entidades import extrair_entidades
from domain.atendimento.conversa.interlocutores import Evidencia, classificar_locutores, pontuar_fala
from domain.atendimento.repositorios import RepositorioAlertaDor, RepositorioConversa, RepositorioSessao

log = logging.getLogger(__name__)


class ServicoConversa:
    def __init__(
        self,
        sessoes: RepositorioSessao,
        conversa: RepositorioConversa,
        alertas: RepositorioAlertaDor,
        camera: ServicoCamera,
        analisador: AnalisadorDeTexto,
        uow: UnidadeDeTrabalho,
        relogio: Relogio,
        ids: GeradorDeId,
    ) -> None:
        self._sessoes = sessoes
        self._conversa = conversa
        self._alertas = alertas
        self._camera = camera
        self._analisador = analisador
        self._uow = uow
        self._relogio = relogio
        self._ids = ids

    def _papeis(self, sessao_id: str) -> dict[str, str]:
        return {loc: info["papel"] for loc, info in self._conversa.locutores(sessao_id).items()}

    def _reclassificar(self, sessao_id: str) -> None:
        info = self._conversa.locutores(sessao_id)
        manuais = {loc: dados["papel"] for loc, dados in info.items() if dados["origem"] == "manual"}
        evidencias: dict[str, Evidencia] = {}
        for fala in self._conversa.falas(sessao_id):
            locutor = fala["locutor"]
            if locutor in regras.SEM_PAPEL_AUTOMATICO or locutor in manuais:
                continue
            evid = evidencias.setdefault(locutor, Evidencia(locutor, 0.0, 0, fala["ordem"]))
            evid.soma += pontuar_fala(fala["texto"])
            evid.falas += 1
        for locutor, (papel, confianca) in classificar_locutores(list(evidencias.values()), manuais).items():
            self._conversa.definir_papel_automatico(sessao_id, locutor, papel, confianca)

    def _sincronizar(self, sessao_id: str) -> None:
        """Alertas de dor só para falas do paciente; termos críticos sem as perguntas do médico."""
        pontos = regras.pontos_visiveis(self._conversa.pontos(sessao_id), self._papeis(sessao_id))
        quando = self._relogio.agora()
        ativos = {a.descricao_sinal.casefold() for a in self._alertas.da_sessao(sessao_id)
                  if a.origem == "relato" and a.ativo}
        for trecho in regras.relatos_de_dor(pontos):
            if trecho.casefold() not in ativos:
                self._alertas.adicionar(AlertaDeDor.abrir(self._ids.novo(), sessao_id, "relato", trecho, quando))
                ativos.add(trecho.casefold())
        sessao = obter_sessao(self._sessoes, sessao_id)
        self._sessoes.salvar(sessao.com_termos(regras.termos_criticos(pontos)))

    def definir_papel(self, sessao_id: str, locutor: str, papel: str) -> None:
        """Correção manual: vence o classificador e não é mais recalculada."""
        obter_sessao(self._sessoes, sessao_id)
        locutor = (locutor or "").strip()
        regras.papel_valido(locutor, papel)
        self._conversa.definir_papel_manual(sessao_id, locutor, papel)
        self._reclassificar(sessao_id)
        self._sincronizar(sessao_id)
        self._uow.commit()

    def _analisar(self, texto: str) -> tuple[str, list[str], str | None]:
        if not self._analisador.configurado():
            return "", [], None
        try:
            analise = self._analisador.analisar(texto)
        except Exception as exc:  # a transcrição não pode parar por falha do Text Analytics
            log.warning("Text Analytics indisponível: %s", exc)
            return "", [], f"Azure Text Analytics indisponivel: {exc}"
        return analise.get("sentiment") or "", list(analise.get("key_phrases") or []), None

    def registrar_fala(self, sessao_id: str, texto: str, *, locutor: str = "", offset_ms: int | None = None) -> dict:
        sessao_em_andamento(self._sessoes, sessao_id)
        texto = (texto or "").strip()
        if not texto:
            raise ValueError("fala vazia")
        locutor = (locutor or "").strip()
        sentimento, frases, aviso = self._analisar(texto)
        pontos = pontos_por_regra(texto) + pontos_por_azure(texto, sentimento, frases)
        agora = self._relogio.agora()
        fala = {
            "id": self._ids.novo(), "ordem": self._conversa.proxima_ordem(sessao_id), "locutor": locutor,
            "texto": texto, "offset_ms": offset_ms, "sentimento": sentimento, "frases_chave": frases,
            "expressao_face": self._camera.expressao_recente(sessao_id, agora=agora), "criado_em": agora,
        }
        self._conversa.adicionar_fala(sessao_id, fala)
        salvos = []
        for ponto in pontos:
            salvo = {**ponto, "id": self._ids.novo(), "fala_id": fala["id"], "criado_em": agora}
            self._conversa.adicionar_ponto(sessao_id, salvo)
            salvos.append({k: v for k, v in salvo.items() if k != "criado_em"})

        self._reclassificar(sessao_id)
        papel = self._papeis(sessao_id).get(locutor, "")
        sessao = obter_sessao(self._sessoes, sessao_id)
        self._sessoes.salvar(sessao.acrescentar_fala(texto, sentimento, papel))
        self._sincronizar(sessao_id)
        self._uow.commit()
        return {
            "fala": {**{k: v for k, v in fala.items() if k != "criado_em"}, "papel": papel,
                     "entidades": extrair_entidades(texto)},
            "pontos": [] if papel == "medico" else salvos,
            "aviso": aviso,
        }

    def transcricao(self, sessao_id: str) -> dict:
        sessao = obter_sessao(self._sessoes, sessao_id)
        locutores = self._conversa.locutores(sessao_id)
        falas = [
            {**fala, "papel": locutores.get(fala["locutor"], {}).get("papel", ""),
             "entidades": extrair_entidades(fala["texto"])}
            for fala in self._conversa.falas(sessao_id)
        ]
        visiveis = regras.pontos_visiveis(self._conversa.pontos(sessao_id), self._papeis(sessao_id))
        return {
            "sessao_id": sessao_id,
            "estado": sessao.estado,
            "locutores": {loc: info["papel"] for loc, info in locutores.items()},
            "locutores_detalhe": locutores,
            "falas": falas,
            "pontos": [{k: v for k, v in p.items() if k not in ("locutor", "papel")} for p in visiveis],
            "resumo_clinico": regras.resumo_clinico(falas),
            "eventos_face": self._camera.eventos(sessao_id),
            "face_atual": self._camera.leitura_atual(sessao_id),
        }
