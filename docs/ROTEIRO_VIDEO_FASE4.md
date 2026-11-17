# Roteiro — vídeo da Fase 4 (até 15 minutos)

Publique no YouTube ou Vimeo (público ou não listado). Narração em português.
**Nunca mostre a chave do Azure** nem o `.env`: no portal, mostre só o nome e o tipo dos recursos Speech e Language.

O enunciado pede que o vídeo mostre **análise de áudio e vídeo**, **resposta a anomalias**, **uso dos serviços Azure** e **o caminho do alerta até a equipe médica**. A tabela abaixo diz em que minuto cada exigência aparece.

## Cobertura do enunciado no vídeo

| Exigência do enunciado | Onde aparece | Tempo |
| --- | --- | --- |
| Vídeo clínico: postura tipo OpenPose | MediaPipe Pose em Internação → Exames | 10:00 |
| Vídeo clínico: objetos e áreas críticas (YOLOv8) | YOLOv8n no mesmo relatório de vídeo | 10:00 |
| Vídeo: rosto do paciente e dor | MediaPipe Face Landmarker (PSPI) + Py-Feat (estágio 2) na consulta | 05:00 |
| Áudio: transcrição (Azure Speech to Text) | Consulta ao vivo com `ConversationTranscriber` (pt-BR) | 03:30 |
| Áudio: sentimento e termos críticos (Azure Text Analytics) | Pontos de atenção da consulta + Exames → Áudio | 04:30 e 10:45 |
| Áudio: alteração vocal (cansaço, respiração) | Traços vocais locais em Exames → Áudio | 10:45 |
| Fusão texto + áudio + vídeo numa leitura | Tela da consulta: conversa, rosto e alertas juntos | 03:30–07:00 |
| Anomalia em sinais vitais com modelo treinado | Sistema → treinar Isolation Forest no PhysioNet 2019 | 11:30 |
| Anomalia em prescrição e movimentação | Internação → Achados (varfarina, salto de dose, imobilidade) | 12:15 |
| Monitoramento em tempo real | Consulta ao vivo + replay do monitor a 1 ponto/s | 13:00 |
| Alerta à equipe médica (ciência e encerramento) | Alertas desta consulta + página `/alertas` | 06:30 e 13:30 |
| Azure Cognitive Services | Portal (nomes dos recursos) + página Sistema | 14:00 |
| Arquitetura e testes | VS Code: 4 projetos em `src/`, 293 testes | 00:45 |

## Antes de gravar (checklist)

- [ ] App rodando (`python -m web.app` ou F5 no VS Code) e aberto em `http://127.0.0.1:5000`
- [ ] `.env` com `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`, `AZURE_LANGUAGE_KEY` e `AZURE_LANGUAGE_ENDPOINT` preenchidos (não abrir o arquivo no vídeo)
- [ ] Py-Feat instalado (`pip install -r requirements-estagio2.txt`), para a cascata de dor mostrar o estágio 2
- [ ] YOLOv8n e MediaPipe baixados (`scripts/download_yolo.py`, `scripts/download_pose.py`); página **Sistema** sem item pendente
- [ ] Corpus PhysioNet baixado (`scripts/download_challenge2019.py`) e áudio demo gerado (`scripts/make_demo_audio.py`)
- [ ] Pelo menos **uma dúvida** já gravada em **Revisão** (faça uma consulta de ensaio antes)
- [ ] Webcam livre ou um vídeo curto para a aba **Exames**
- [ ] Duas pessoas para a consulta ao vivo (médico e paciente), ou uma pessoa alternando as falas
- [ ] Fechar notificações, abas extras e o `.env`; zoom do navegador em 110–125% para legibilidade

## Roteiro

Cada bloco traz **o que mostrar** e **a fala sugerida**. Os tempos somam 15:00; se estourar, encurte a arquitetura e o fechamento.

### 00:00 – 00:45 · Abertura

**Tela:** página **Hoje**.
**Ação:** alterne o tema **Claro / Escuro / Auto** no topo e volte para Auto.

> "Este é o consultório multimodal da Fase 4. Ele acompanha a consulta com câmera e microfone, lê fala, rosto e movimentação numa tela só e transforma o que precisa de atenção em alertas para o médico. É uma demonstração educacional: não prescreve, não dá diagnóstico e não diz se o paciente mente ou fala a verdade. A página Hoje mostra as consultas em andamento e o que pede ação."

### 00:45 – 01:45 · Arquitetura e testes

**Tela:** VS Code, árvore de `src/`, depois `src/Web/web/dependencias.py` e o terminal.
**Ação:** rode `python -m pytest -q` (ou mostre a última execução).

> "O código segue quatro projetos, como uma solution: Domain com as regras, Application com os casos de uso e as portas, Infrastructure com SQLite, MediaPipe, YOLO, Py-Feat, Azure e PhysioNet, e Web, que é o MVC em Flask. As dependências são montadas num único arquivo com o injector. São 293 testes: unitários com fakes em memória, integração com banco e modelos reais, e um teste de arquitetura que impede o domínio de depender da infraestrutura."

### 01:45 – 02:30 · Cadastro do paciente

**Tela:** **Pacientes**.
**Ação:** cadastre "Ana Lima"; tente cadastrar sem nome (recusado); abra a ficha e tente excluir (recusado).

> "O cadastro é do consultório. As séries do PhysioNet não aparecem aqui: elas são corpus de treino, não prontuário. Sem nome o cadastro é recusado, e a exclusão também, para o histórico das consultas não se perder."

### 02:30 – 03:30 · Preparar a consulta

**Tela:** ficha de Ana Lima → **Nova consulta** → **Preparar**.
**Ação:** **Testar microfone** e **Testar câmera**; aponte o aviso de consentimento e o quadro **Recursos desta máquina**; clique em **Começar atendimento**.

> "Antes de começar, o médico testa microfone e câmera. O aviso informa ao paciente que a imagem não sai deste computador e que só os momentos de dúvida da leitura de dor ficam gravados para revisão. Ao lado, os recursos da máquina mostram se o Azure, os modelos de visão e o validador de dor estão disponíveis."

### 03:30 – 07:00 · Consulta ao vivo (bloco principal: áudio + vídeo + fusão)

**Tela:** **Consulta**, com a câmera no topo.
**Ação:** **Iniciar consulta ao vivo** e **Ligar câmera**. Siga o diálogo abaixo.

Diálogo sugerido (M = médico, P = paciente):

1. M: "Bom dia, o que trouxe a senhora aqui hoje?"
2. P: "Estou com uma dor nas costas faz três dias. Não tive febre."
3. M: "Essa dor piora quando a senhora se movimenta?"
4. P: "Piora. Às vezes dá uma pontada forte e fico sem fôlego." *(careta de dor por 3 a 4 segundos)*
5. P: "Desde ontem estou mancando um pouco."

**03:30 – 04:30 · Fala (Azure Speech).**

> "A fala vai para o Azure Speech to Text com o ConversationTranscriber em português, que separa as vozes. O sistema deduz quem é o médico e quem é o paciente pelas pistas da fala, como perguntas e relato em primeira pessoa, e o médico pode corrigir se errar."

**04:30 – 05:00 · Pontos de atenção (Azure Text Analytics).** Aponte os trechos destacados e o card **Pontos de atenção**.

> "Cada fala do paciente é marcada com pontos de atenção. Repare que 'não tive febre' não vira febre: as regras tratam negação. O sentimento vem do Azure Text Analytics. O Resumo clínico junta queixa, tempo e sintomas para o médico conferir."

**05:00 – 06:30 · Rosto e cascata de dor (vídeo).** Abra **Detalhes da leitura** da câmera e mostre o card **Dor agora**.

> "O rosto é lido no navegador pelo MediaPipe Face Landmarker, com 52 blendshapes. Deles saem a expressão e um indicador de dor estruturado como o PSPI, calibrado pelo rosto neutro do próprio paciente. Dor leve por 3 segundos é só uma suspeita: o navegador manda três recortes do rosto ao servidor local, e o Py-Feat, que detecta as unidades de ação faciais, confirma ou descarta. Só a confirmação abre o alerta. O resultado aparece na escala de faces Wong-Baker, como estimativa observacional."

**Ação:** toque na face Wong-Baker que a paciente apontar.

> "A face que o paciente aponta fica gravada ao lado da estimativa da câmera, para medir a concordância entre as duas."

**06:30 – 07:00 · Alerta na consulta.** Mostre **Alertas desta consulta**: origem rosto, relato (pontada) e movimentação (mancando). Clique em **Ciente** em um deles.

> "A dor pode chegar por três caminhos: pelo rosto, por um relato como 'pontada' ou pela movimentação, como mancar. Qualquer um basta para abrir o alerta. O médico dá ciência aqui mesmo, e o alerta continua aberto até ele encerrar."

### 07:00 – 08:00 · Encerrar e relatório

**Tela:** **Encerrar** → **Encerrar e ver relatório**.
**Ação:** encerre um alerta pendente; percorra o relatório: Dor apontada, Observações, Pontos de atenção, Resumo clínico, Transcrição completa.

> "Ao encerrar, o médico revisa os pontos de atenção e fecha os alertas. O relatório traz a dor apontada pela câmera e pelo paciente, os desvios da consulta e a transcrição completa. Ele não prescreve e não é escore validado de dor."

### 08:00 – 09:15 · Revisão de dúvidas

**Tela:** **Revisão** → abra uma dúvida pendente.
**Ação:** deixe o recorte rodar em loop; marque a face Wong-Baker real, a categoria e uma observação; **Salvar e ir para a próxima**.

> "Quando a câmera e o validador discordam, ou ficam perto do limite, o sistema grava de 2 a 4 segundos de recortes do rosto, só neste computador. O médico assiste e classifica com a face real, uma categoria e uma observação. Assim cada dúvida vira um exemplo rotulado para calibrar os limiares, que hoje são heurísticos."

### 09:15 – 10:00 · Internação (contexto)

**Tela:** **Internação** com o paciente `p000003`.

> "A segunda parte é a internação, com pacientes da base PhysioNet Challenge 2019. Aqui ficam os exames de vídeo e áudio, os achados de sinais vitais, prescrição e movimentação, e o monitor do plantão."

### 10:00 – 11:30 · Exames: vídeo e áudio

**Tela:** **Internação → Exames**.

**10:00 – 10:45 · Vídeo.** **Ligar webcam** e grave 5 s levantando o braço lateralmente (abdução do ombro), com um celular à vista; ou envie um arquivo. Clique em **Analisar vídeo**.

> "O vídeo passa pelo MediaPipe Pose, que extrai os pontos do corpo como o OpenPose citado no enunciado, e roda no Windows sem compilar o OpenPose. O YOLOv8n detecta objetos e áreas críticas no quadro, como o celular. O relatório mostra o desvio de postura e o objeto encontrado."

**10:45 – 11:30 · Áudio.** Clique em **Usar amostra**, depois **Analisar áudio**.

> "O áudio vai ao Azure Speech para a transcrição e ao Azure AI Language para sentimento e frases-chave. Localmente, os traços vocais apontam pausas e sinais de cansaço ou falta de ar. É alteração vocal, não diagnóstico. Na amostra aparecem o termo crítico 'falta de ar' e o sentimento negativo."

### 11:30 – 13:00 · Anomalias

**11:30 – 12:15 · Modelo treinado.** **Tela:** **Sistema → Anomalia de padrão**. Clique em **Treinar novo modelo**; avalie a série `p000003`, depois `p000057`; marque a opção de faixa fixa e mostre a recusa.

> "A anomalia de sinais vitais usa um Isolation Forest treinado no corpus PhysioNet, com até 8 mil leituras horárias de frequência cardíaca, pressão sistólica e diastólica e saturação. O rótulo de sepse não entra no treino. A série p000003 sai como anômala e aponta oxigenação e pressão; a p000057 é compatível com o padrão. Uma detecção só com faixas fixas é recusada, porque o requisito pede modelo treinado."

**12:15 – 13:00 · Prescrição e movimentação.** **Tela:** **Internação**, card **Achados**, paciente `p000003`. Clique em **Enviar alertas**.

> "No mesmo paciente aparecem as anomalias de prescrição, como início de varfarina e salto de dose de AAS de duas vezes ou mais, e de movimentação, como imobilidade de 4 horas ou mais e saída noturna no corredor. Com um clique, os achados viram alertas para a equipe."

### 13:00 – 14:00 · Tempo real e caminho do alerta

**13:00 – 13:30 · Monitor.** **Tela:** **Internação → Monitor**. **Iniciar replay**.

> "O monitor reproduz a série do plantão a um ponto por segundo, como à beira do leito. Quando a saturação ou a diastólica saem da faixa, o alerta dispara na hora daquele ponto."

**13:30 – 14:00 · `/alertas`.** **Tela:** **Alertas**, abas da consulta e da internação. Clique em **Ciente** e depois **Encerrar** em um alerta de cada aba.

> "Todos os alertas chegam aqui, separados por origem: dor nas consultas e anomalias da internação. O médico dá ciência, o alerta continua visível, e ao encerrar ele sai da fila. Esse é o caminho completo, do sinal até a ação da equipe."

### 14:00 – 14:30 · Azure

**Tela:** portal do Azure, só o grupo de recursos com **Speech** e **Language** (nome, tipo e região). Volte ao app, página **Sistema → Serviços e modelos**.

> "Estes são os dois serviços cognitivos usados: Azure Speech, para a transcrição com separação de vozes, e Azure AI Language, para sentimento e frases-chave. A chave fica no servidor; o navegador recebe só um token temporário. A análise do rosto é local porque a Microsoft descontinuou a detecção de emoção do Azure Face, e assim a imagem não sai da máquina."

### 14:30 – 15:00 · Fechamento

**Tela:** página **Hoje** ou o relatório técnico.

> "Em resumo: fala, rosto e movimentação lidos juntos na consulta, anomalia aprendida em dados históricos, Azure para fala e texto, e um caminho claro do alerta até o médico. Os limites estão no relatório técnico: as faixas de dor são heurísticas, a Wong-Baker é autorrelato, e o sistema é de apoio, nunca de decisão. O código e o relatório estão no repositório."

## Entrega

- [ ] Vídeo gravado com até 15 minutos
- [ ] Publicado no YouTube ou Vimeo (público ou não listado)
- [ ] Link do vídeo colado na entrega da pós e no README
- [ ] Repositório e relatório técnico (`docs/RELATORIO_TECNICO_FASE4.md`) enviados

Apoio educacional. Dados sintéticos e PhysioNet; não usar com paciente real.
