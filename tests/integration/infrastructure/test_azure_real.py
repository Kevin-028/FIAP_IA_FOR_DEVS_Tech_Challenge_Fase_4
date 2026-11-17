"""Azure Speech e Azure AI Language de verdade. Só roda com --azure ou RUN_AZURE_TESTS=1."""
from __future__ import annotations

import os

import pytest

from infrastructure.caminhos import HOSPITAL_DATA

pytestmark = pytest.mark.azure

AMOSTRA = os.path.join(HOSPITAL_DATA, "fase4", "samples", "consulta.wav")


@pytest.fixture(autouse=True)
def precisa_chaves(project_root):
    from dotenv import load_dotenv

    from infrastructure.azure.language import missing_language
    from infrastructure.azure.speech import missing_speech

    load_dotenv(os.path.join(project_root, ".env"))
    faltam = missing_speech() + missing_language()
    if faltam:
        pytest.skip("faltam no .env: " + ", ".join(faltam))


def test_token_do_speech():
    from infrastructure.azure.speech import issue_speech_token

    cred = issue_speech_token()
    assert cred["region"] and len(cred["token"]) > 100


def test_text_analytics_sentimento_e_frases_chave():
    from domain.atendimento.conversa.atencao import pontos_por_regra
    from domain.plantao.audio import critical_terms
    from infrastructure.azure.language import analyze_text

    texto = "Doutor, estou com muita falta de ar e com medo de piorar."
    out = analyze_text(texto)
    assert out["sentiment"] in ("negative", "mixed")
    assert out["key_phrases"]
    # o Azure quebra "falta de ar" em "muita falta" + "ar"; a transcrição recupera o termo
    assert "falta de ar" in critical_terms(out["key_phrases"], pontos_por_regra(texto))


@pytest.mark.skipif(not os.path.isfile(AMOSTRA), reason="rode python scripts/make_demo_audio.py")
def test_speech_transcreve_a_amostra():
    from infrastructure.azure.speech import transcribe_wav

    assert transcribe_wav(AMOSTRA).strip()


@pytest.mark.skipif(not os.path.isfile(AMOSTRA), reason="rode python scripts/make_demo_audio.py")
def test_rota_de_audio_com_azure(client):
    r = client.post("/api/fase4/audio", data={"patient_id": "p000003", "use_sample": "1"})
    assert r.status_code == 200
    report = r.get_json()["report"]
    assert report["transcript"] and report["sentiment"]


def test_fala_da_consulta_com_text_analytics(client, conn):
    client.post("/pacientes", data={"nome": "Azure Teste"})
    paciente_id = conn.execute("SELECT id FROM pacientes WHERE nome = 'Azure Teste'").fetchone()["id"]
    sessao = client.post("/sessoes", data={"paciente_id": paciente_id}).headers["Location"].split("/")[-1]
    out = client.post(f"/api/sessoes/{sessao}/falas",
                      json={"texto": "Estou péssima, com dor no peito desde ontem.", "locutor": "Guest-2"}).get_json()
    assert out["aviso"] is None and out["fala"]["sentimento"]
    assert "Dor torácica" in {p["categoria"] for p in out["pontos"]}
