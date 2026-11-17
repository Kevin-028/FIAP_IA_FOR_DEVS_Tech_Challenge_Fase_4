"""Plantão multimodal da Fase 4: vídeo, áudio, vitais, prescrição e movimento fundidos na fila de alertas."""
from __future__ import annotations

from application.plantao.portas import (
    AnalisadorDeTextoPlantao,
    AnalisadorDeVideo,
    AnalisadorDeVoz,
    AudioSemServicoExterno,
    DetectorDeOutliers,
    FonteDeSeries,
    Transcritor,
)
from application.portas import Relogio, UnidadeDeTrabalho
from domain.atendimento.conversa.atencao import pontos_por_regra
from domain.plantao.alerta import achados_para_alerta, fio_do_paciente
from domain.plantao.audio import audio_report
from domain.plantao.fusion import fuse
from domain.plantao.movement import movement_anomalies
from domain.plantao.prescriptions import prescription_anomalies
from domain.plantao.repositorios import RepositorioAlertaPlantao, RepositorioPlantao
from domain.plantao.vitals import avaliar_medicao, vital_anomalies

REGISTRO_AUSENTE = "Registro não encontrado na base do Challenge 2019."


class ServicoPlantao:
    def __init__(
        self,
        plantao: RepositorioPlantao,
        alertas: RepositorioAlertaPlantao,
        fonte: FonteDeSeries,
        outliers: DetectorDeOutliers,
        transcritor: Transcritor,
        analisador: AnalisadorDeTextoPlantao,
        voz: AnalisadorDeVoz,
        video: AnalisadorDeVideo,
        uow: UnidadeDeTrabalho,
    ) -> None:
        self._plantao = plantao
        self._alertas = alertas
        self._fonte = fonte
        self._outliers = outliers
        self._transcritor = transcritor
        self._analisador = analisador
        self._voz = voz
        self._video = video
        self._uow = uow

    # --- registro do paciente da base PhysioNet ---------------------------------------------
    def paciente_padrao(self) -> str:
        return self._fonte.paciente_padrao()

    def pacientes(self) -> list[dict]:
        return self._plantao.pacientes_challenge()

    def abrir_registro(self, patient_id: str) -> str | None:
        """Carrega o registro no plantão se ainda não estiver lá; devolve o erro quando não existe."""
        item = self._fonte.serie(patient_id)
        if item is None:
            return REGISTRO_AUSENTE
        falta = (self._plantao.paciente(patient_id) is None or not self._plantao.vitais(patient_id)
                 or not self._plantao.prescricoes(patient_id))
        if falta:
            self._plantao.gravar_registro(item)
            self._uow.commit()
        return None

    def fonte_vital(self, patient_id: str) -> str | None:
        item = self._fonte.serie(patient_id)
        return item["notes"] if item else None

    def _prontuario(self, patient_id: str) -> str:
        paciente = self._plantao.paciente(patient_id) or {}
        return " ".join(parte for parte in (paciente.get("diagnosis"), paciente.get("notes")) if parte)

    # --- leituras ----------------------------------------------------------------------------
    def anomalias(self, patient_id: str) -> dict:
        return {
            "vitals": vital_anomalies(self._plantao.vitais(patient_id), self._outliers.detectar),
            "prescriptions": prescription_anomalies(self._plantao.prescricoes(patient_id)),
            "movement": movement_anomalies(self._plantao.movimentos(patient_id)),
        }

    def painel(self, patient_id: str) -> dict:
        achados = self.anomalias(patient_id)
        tipos = self._plantao.tipos_de_relatorio(patient_id)
        abertos_do_paciente = sum(1 for a in self._alertas.listar("open") if a.get("patient_id") == patient_id)
        return {
            "vitals_count": len(self._plantao.vitais(patient_id)),
            "vitals_hits": len(achados["vitals"]),
            "rx_hits": len(achados["prescriptions"]),
            "move_hits": len(achados["movement"]),
            "done_video": "video" in tipos,
            "done_audio": "audio" in tipos,
            "open_alerts_patient": abertos_do_paciente,
            "open_alerts_total": self._alertas.abertos(),
        }

    def serie(self, patient_id: str) -> dict:
        return {"patient_id": patient_id, "vitals": self._plantao.vitais(patient_id),
                "movement": self._plantao.movimentos(patient_id)}

    # --- fusão e fila de alertas ---------------------------------------------------------------
    def _fundir(self, patient_id: str, *, video=None, audio=None) -> dict:
        achados = self.anomalias(patient_id)
        return fuse(video=video, audio=audio, vitals=achados["vitals"], prescriptions=achados["prescriptions"],
                    movement=achados["movement"], chart_text=self._prontuario(patient_id))

    def _publicar(self, patient_id: str, resultado: dict) -> list[str]:
        fio = fio_do_paciente(patient_id)
        criados = [a["reason"] for a in achados_para_alerta(resultado) if self._alertas.emitir(patient_id, fio, a)]
        self._uow.commit()
        return criados

    def alertas_da_fusao(self, patient_id: str) -> dict:
        resultado = self._fundir(patient_id)
        return {"level": resultado["level"], "new_alerts": self._publicar(patient_id, resultado)}

    def processar_video(self, caminho: str, patient_id: str) -> dict:
        relatorio, aviso = self._video.analisar(caminho)
        self.abrir_registro(patient_id)
        criados = self._publicar(patient_id, self._fundir(patient_id, video=relatorio))
        self._plantao.salvar_relatorio(patient_id, "video", relatorio)
        self._uow.commit()
        return {"report": relatorio, "new_alerts": criados, "warning": aviso, "prescribes": False}

    def processar_audio(self, caminho_wav: str, patient_id: str) -> dict:
        amostras, taxa = self._voz.ler_wav(caminho_wav)
        vocal = self._voz.caracteristicas(amostras, taxa)
        faltando = self._transcritor.faltando() + self._analisador.faltando()
        if faltando:
            raise AudioSemServicoExterno(faltando, vocal)
        transcricao = self._transcritor.transcrever(caminho_wav)
        relatorio = audio_report(transcricao, self._analisador.analisar(transcricao),
                                 pontos_por_regra(transcricao or ""), vocal)
        self.abrir_registro(patient_id)
        criados = self._publicar(patient_id, self._fundir(patient_id, audio=relatorio))
        self._plantao.salvar_relatorio(patient_id, "audio", relatorio)
        self._uow.commit()
        return {"report": relatorio, "new_alerts": criados, "prescribes": False}

    # --- monitor ponto a ponto ----------------------------------------------------------------
    def resetar_monitor(self, patient_id: str) -> None:
        self._plantao.limpar_monitor(patient_id, fio_do_paciente(patient_id))
        self._uow.commit()

    def tick(self, patient_id: str, *, vital: dict | None, movement: dict | None) -> dict:
        if vital is not None:
            self._plantao.adicionar_vital(patient_id, vital)
        if movement is not None:
            self._plantao.adicionar_movimento(patient_id, movement)
        self._uow.commit()
        resultado = self._fundir(patient_id)
        avaliacao = None
        if vital is not None:  # leitura ao vivo: o estado desta medição no contexto da série inteira
            avaliacao = avaliar_medicao(vital, vital_anomalies(self._plantao.vitais(patient_id), self._outliers.detectar))
        return {"level": resultado["level"], "new_alerts": self._publicar(patient_id, resultado), "fusion": resultado,
                "avaliacao": avaliacao}


class ServicoAlertasPlantao:
    """Fila da equipe: listar, reconhecer e fechar."""

    def __init__(self, alertas: RepositorioAlertaPlantao, uow: UnidadeDeTrabalho, relogio: Relogio) -> None:
        self._alertas = alertas
        self._uow = uow
        self._relogio = relogio

    def listar(self, status: str | None = None) -> list[dict]:
        return self._alertas.listar(status)

    def abertos(self) -> int:
        return self._alertas.abertos()

    def reconhecer(self, alerta_id: int) -> None:
        alerta = self._alertas.obter(alerta_id)
        if alerta is not None:
            self._alertas.salvar(alerta.reconhecer(self._relogio.agora()))
            self._uow.commit()

    def fechar(self, alerta_id: int) -> None:
        alerta = self._alertas.obter(alerta_id)
        if alerta is not None:
            self._alertas.salvar(alerta.fechar(self._relogio.agora()))
            self._uow.commit()
