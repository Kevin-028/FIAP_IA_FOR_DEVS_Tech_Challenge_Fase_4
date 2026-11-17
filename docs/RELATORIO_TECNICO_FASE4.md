# Relatório técnico — Tech Challenge Fase 4

Demo educacional de consultório/plantão multimodal (FIAP). O sistema **não prescreve**. Cada achado entra na fila `/alertas`, onde a equipe pode **reconhecer** e **fechar**.

## Cobertura do enunciado (PDF)

| Requisito obrigatório | Cobertura |
| --- | --- |
| Análise de vídeo clínico + postura (tipo OpenPose) + YOLOv8 + relatório | **Sim** — MediaPipe Pose + YOLOv8n; upload ou webcam |
| Análise de áudio + fadiga/respiração + Azure Speech + Text Analytics | **Sim** — traços vocais locais + Azure Speech/Language |
| Anomalias em vitais, prescrições e movimentação + alertas | **Sim** — regras + Isolation Forest; Rx e movimento do plantão demo |
| Fusão texto/áudio/vídeo + Azure Cognitive Services | **Sim** — `fuse` + `publish` |
| Monitoramento preventivo em tempo real | **Sim (demo)** — replay 1 ponto/s no monitor; captura ao vivo de vídeo/áudio |
| Relatório técnico (fluxo, modelos, exemplos) | **Este documento** |
| Repositório com código-fonte | Projeto `Fase_4` |
| Vídeo ≤15 min YouTube/Vimeo | Roteiro em `DOCS/ROTEIRO_VIDEO_FASE4.md` (gravação/publicação pelo aluno) |

## Fluxo multimodal (consultório demo)

1. Abre-se a **consulta** em `/fase4` com paciente PhysioNet (`p000003` risco ou `p000057` estável).
2. **Vídeo**: arquivo ou webcam → MediaPipe Pose + YOLOv8n → relatório e alertas.
3. **Áudio**: WAV ou amostra → fadiga local; Azure Speech (pt-BR) e Azure AI Language (sentimento + key phrases).
4. **Anomalias**: vitais PhysioNet + evolução clínica do plantão (Rx/movimento) → **Gerar alertas**.
5. **Monitor**: replay 1 Hz da série; SpO2/DBP ruins disparam na hora do ponto.
6. **Equipe** em `/alertas`: reconhecer (`acked`) e fechar (`closed`).

## Modelos por tipo de dado

| Dado | Modelo |
| --- | --- |
| Postura | mediapipe-pose. MediaPipe Pose cumpre a tarefa de keypoints citada como OpenPose e roda no Windows sem compilar o OpenPose. |
| Objeto e área crítica | yolov8n |
| Fala | Azure Speech to Text |
| Sentimento e termos críticos | Azure AI Language (Text Analytics) |
| Sinais vitais | Regras (SpO2, FC, PAS, PAD) e Isolation Forest |
| Prescrição | Início de droga de alerta e salto de dose ≥ 2× |
| Movimentação | Imobilidade ≥ 4 h e saída noturna no corredor |

## Resultados e exemplos

- Vídeo: desvio de shoulder_abduction e objeto crítico (ex.: celular no campo).
- Áudio: fadiga por pausa; termo crítico “falta de ar”; sentimento negativo (amostra + Azure).
- Vitais: `p000057` estável; `p000003` com SpO2/DBP fora da faixa (PhysioNet Challenge 2019).
- Prescrição/movimento: varfarina, salto de AAS, imobilidade e saída noturna no mesmo ID (evolução do plantão demo).
- Tempo real da demo: monitor a 1 Hz + captura ao vivo de mídia.

Datasets: [PhysioNet Challenge 2019](https://www.physionet.org/content/challenge-2019/1.0.0/). AudioSet não traz consulta médica; o áudio demo é fala sintetizada.

Apoio educacional. Dados sintéticos/PhysioNet — não usar com paciente real.
