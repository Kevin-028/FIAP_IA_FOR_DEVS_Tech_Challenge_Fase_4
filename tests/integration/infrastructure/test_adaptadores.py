"""Adaptadores sem rede: Isolation Forest, traços vocais, Azure sem chave, WAV de demo e avaliação offline."""
from __future__ import annotations

import wave

import numpy as np
import pytest

from application.atendimento.portas import ServicoExternoNaoConfigurado
from domain.plantao.video_report import OPENPOSE_NOTE
from infrastructure.azure.language import AnalisadorAzure, analyze_text
from infrastructure.azure.speech import AzureNotConfigured, issue_speech_token, transcribe_wav
from infrastructure.ia.isolation_forest import MotorIsolationForest
from infrastructure.ia.outliers import DetectorIsolationForest, isolation_outlier_indexes
from infrastructure.ia.voz import AnalisadorDeVozNumpy, vocal_features

RATE = 16000


def _tom(segundos: float, amp: float = 0.2):
    return amp * np.sin(2 * np.pi * 220 * np.arange(int(RATE * segundos)) / RATE)


def test_isolation_forest_aponta_outlier_multivariado():
    matriz = [[80 + (h % 3), 120 + (h % 2), 80, 97] for h in range(30)]
    matriz[20] = [118, 175, 105, 93]
    assert 20 in DetectorIsolationForest().detectar(matriz)


def test_isolation_forest_precisa_de_24_pontos_e_variacao():
    assert isolation_outlier_indexes([[80, 120, 80, 97]] * 10) == []
    assert isolation_outlier_indexes([[80, 120, 80, 97]] * 30) == []


def test_motor_de_anomalia_compativel_e_anomalo():
    normal = [{"hr": 80 + (i % 5), "sbp": 120 + (i % 7), "dbp": 80 + (i % 3), "spo2": 97 + (i % 2)} for i in range(200)]
    motor = MotorIsolationForest()
    artefato = motor.treinar(normal)
    picos = motor.picos_anomalos(artefato, [{"hr": 160, "sbp": 120, "dbp": 80, "spo2": 80}])
    assert len(picos) == 4 and picos[0] > 2 and picos[3] > 2


def test_fala_continua_sem_fadiga():
    feat = vocal_features(_tom(2), RATE)
    assert feat["fatigue"] is False and feat["pause_ratio"] < 0.1


def test_muitas_pausas_indicam_fadiga():
    feat = vocal_features(np.concatenate([_tom(1), np.zeros(RATE)]), RATE)
    assert feat["fatigue"] is True and feat["respiratory_effort"] is False


def test_pausas_com_fala_fraca_indicam_esforco_respiratorio():
    feat = vocal_features(np.concatenate([_tom(1, amp=0.04), np.zeros(2 * RATE)]), RATE)
    assert feat["fatigue"] is True and feat["respiratory_effort"] is True


def test_audio_vazio_nao_quebra():
    assert vocal_features([], RATE)["fatigue"] is True


def test_leitura_de_wav(wav_silencio):
    amostras, taxa = AnalisadorDeVozNumpy().ler_wav(wav_silencio)
    assert taxa == RATE and len(amostras) == RATE


def test_speech_sem_chave_lista_variaveis(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF")
    with pytest.raises(AzureNotConfigured) as erro:
        transcribe_wav(str(wav))
    assert erro.value.missing == ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"]
    assert isinstance(erro.value, ServicoExternoNaoConfigurado)  # a Web trata pela porta, sem conhecer o Azure


def test_token_sem_chave():
    with pytest.raises(AzureNotConfigured):
        issue_speech_token()


def test_language_sem_chave():
    with pytest.raises(AzureNotConfigured) as erro:
        analyze_text("oi")
    assert "AZURE_LANGUAGE_ENDPOINT" in erro.value.missing
    assert AnalisadorAzure().configurado() is False


def test_wav_demo(tmp_path):
    from scripts.make_demo_audio import wav_is_demo

    path = tmp_path / "consulta.wav"
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(np.zeros(RATE, dtype=np.int16).tobytes())
    assert wav_is_demo(str(path)) is True


def test_avaliacao_offline_cita_datasets():
    from analises.avaliacao_offline import run

    result = run()
    assert result["video"]["summary"].startswith("Desvio detectado")
    assert result["video"]["openpose_note"] == OPENPOSE_NOTE
    assert result["fusion"]["prescribes"] is False
    assert "https://physionet.org/" in result["datasets"]["urls"]


def test_registro_physionet_nunca_expoe_sepse():
    from infrastructure.physionet.challenge2019 import read_record, series_of

    serie = series_of("p000003")
    assert serie is not None and "sepse" not in serie["diagnosis"].casefold()
    assert all("sepsis" not in linha for linha in serie["rows"])
    caminho = __import__("infrastructure.physionet.challenge2019", fromlist=["find_path"]).find_path("p000057")[2]
    assert set(read_record(caminho)[0]) == {"recorded_at", "hr", "sbp", "dbp", "spo2"}
