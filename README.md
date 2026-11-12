# Tech Challenge — Fase 4 | FIAP

Demo educacional de **consultório/plantão multimodal**: vídeo (MediaPipe Pose + YOLOv8), áudio (Azure Speech/Language), anomalias (vitais PhysioNet + Rx/movimento do plantão), fusão e alertas com reconhecer/fechar.

Pacientes demo: `p000057` (estável) e `p000003` (risco).

> Demo educacional. Dados PhysioNet/sintéticos — não usar com paciente real. Não substitui avaliação médica e não emite prescrição.

## Setup

```powershell
cd C:\workspace\FIAP\IA_DEVs\Tech_Challenge\Fase_4
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Preencha AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, AZURE_LANGUAGE_KEY, AZURE_LANGUAGE_ENDPOINT

python -m multimodal.download_yolo
python -c "from multimodal.challenge2019 import save_choice; save_choice()"
python -m hospital.seed
python scripts/make_demo_audio.py
python web/app.py
```

O repo já inclui `p000003.psv` e `p000057.psv`. Para a base completa (~40k arquivos):

```powershell
python scripts/download_challenge2019.py
python -c "from multimodal.challenge2019 import save_choice; save_choice()"
python -m hospital.seed
```

## VS Code / Cursor

1. Abra a pasta `Fase_4` como workspace.
2. Interpretador `.venv` (`.vscode/settings.json`).
3. **Run and Debug** → **Flask: Fase 4** ou **Python: web/app.py** → F5.
4. http://127.0.0.1:5000/fase4

Tarefas: Terminal → Run Task → **Seed plantão** / **pytest Fase 4**.

## Páginas

| Rota | Função |
| --- | --- |
| `/fase4` | Hub da consulta (checklist + disclaimer) |
| `/fase4/video` | Arquivo ou webcam → Pose + YOLO |
| `/fase4/audio` | WAV / amostra → Azure + traço vocal |
| `/fase4/anomalias` | Vitais, Rx, movimento + publicar |
| `/fase4/monitor` | Replay 1 Hz |
| `/alertas` | Fila da equipe (reconhecer / fechar) |

## Entrega da pós

1. Código neste repositório (faça `git commit` local; `git remote` + push se a instituição pedir).
2. Relatório: [DOCS/RELATORIO_TECNICO_FASE4.md](DOCS/RELATORIO_TECNICO_FASE4.md)
3. Vídeo ≤15 min: siga [DOCS/ROTEIRO_VIDEO_FASE4.md](DOCS/ROTEIRO_VIDEO_FASE4.md) e publique no YouTube/Vimeo.

## Documentos

- [DOCS/RELATORIO_TECNICO_FASE4.md](DOCS/RELATORIO_TECNICO_FASE4.md)
- [DOCS/ROTEIRO_VIDEO_FASE4.md](DOCS/ROTEIRO_VIDEO_FASE4.md)
- [DOCS/EVIDENCIA_UI_FASE4.md](DOCS/EVIDENCIA_UI_FASE4.md)
