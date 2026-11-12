# Roteiro — vídeo da Fase 4 (até 15 minutos)

Publique no YouTube ou Vimeo (público ou não listado). **Não mostre a chave Azure.** Mostre só o nome dos recursos Speech e Language.

## Checklist do aluno (entrega)

- [ ] App rodando (`python web/app.py` ou F5 no VS Code)
- [ ] Gravou o vídeo ≤ 15 min na ordem abaixo
- [ ] Publicou no YouTube ou Vimeo
- [ ] Colou o link na entrega da pós
- [ ] (Opcional) `git remote` + push do repositório

## Ordem obrigatória

| Tempo | O que mostrar |
| --- | --- |
| 0:00 | Hub `/fase4` (Consulta/Plantão), paciente `p000003`, disclaimer educacional. Diga que o sistema não prescreve. |
| 2:00 | **Análise de vídeo** em `/fase4/video`: webcam 5 s ou arquivo; relatório MediaPipe + YOLOv8n. |
| 5:00 | **Análise de áudio** em `/fase4/audio`: **Usar amostra**; transcrição, sentimento, termo crítico. |
| 8:00 | **Anomalia** em `/fase4/anomalias`: SpO2/DBP, varfarina, imobilidade. **Gerar alertas deste plantão**. |
| 11:00 | **Azure**: portal só o bastante para Speech e Language. Volte e mostre a transcrição. |
| 13:00 | **Monitor** Reproduzir plantão (replay 1 Hz) e **/alertas**: Reconhecer e Fechar um alerta. |
| 14:30 | Encerre. |

Ordem obrigatória do PDF: análise de vídeo → análise de áudio → anomalia → Azure → `/alertas`.
