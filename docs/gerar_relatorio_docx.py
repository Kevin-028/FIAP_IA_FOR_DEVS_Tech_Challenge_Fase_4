"""Gera o relatório técnico Word da Fase 4 no mesmo visual das Fases 2 e 3."""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Twips

FIAP_RED = RGBColor(0xEF, 0x33, 0x40)
DARK = RGBColor(0x1A, 0x1A, 0x1A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
HEADER_FILL = "EF3340"
ALT_ROW = "F7F7F7"
REPO = "https://github.com/Kevin-028/FIAP_IA_FOR_DEVS_Tech_Challenge_Fase_4"
VIDEO = "Link a ser inserido após a gravação"
OUT = Path(__file__).with_name("Relatorio_Tecnico_TechChallenge_Fase4_FIAP.docx")


def _run(paragraph, text, *, size=11, bold=False, color=DARK, font="Calibri"):
    run = paragraph.add_run(text)
    run.font.name = font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return run


def _set_spacing(paragraph, after=120, before=0, line=None):
    pf = paragraph.paragraph_format
    pf.space_after = Twips(after)
    pf.space_before = Twips(before)
    if line is not None:
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE


def cover(doc, text, *, size, bold, after, color=DARK):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_spacing(p, after=after)
    _run(p, text, size=size, bold=bold, color=color)
    return p


def h1(doc, text):
    p = doc.add_paragraph(style="Heading 1")
    p.clear()
    _run(p, text, size=14, bold=True, color=FIAP_RED)
    return p


def h2(doc, text):
    p = doc.add_paragraph(style="Heading 2")
    p.clear()
    _run(p, text, size=12, bold=True, color=DARK)
    return p


def h3(doc, text):
    p = doc.add_paragraph(style="Heading 3")
    p.clear()
    _run(p, text, size=11, bold=True, color=DARK)
    return p


def body(doc, text, after=120):
    p = doc.add_paragraph()
    _set_spacing(p, after=after, before=0)
    _run(p, text, size=11, bold=False, color=DARK)
    return p


def bold_line(doc, text, after=80):
    p = doc.add_paragraph()
    _set_spacing(p, after=after)
    _run(p, text, size=11, bold=True, color=DARK)
    return p


def code(doc, text):
    p = doc.add_paragraph()
    _set_spacing(p, after=80)
    _run(p, text, size=10, bold=False, color=DARK, font="Consolas")
    return p


def bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.clear()
    _set_spacing(p, after=40)
    _run(p, text, size=11, bold=False, color=DARK)
    return p


def shade(cell, fill):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def set_cell_border(cell):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "D0D0D0")
        tcBorders.append(el)
    tcPr.append(tcBorders)


def table(doc, headers, rows):
    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
    tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, header in enumerate(headers):
        cell = tbl.rows[0].cells[i]
        cell.text = ""
        shade(cell, HEADER_FILL)
        set_cell_border(cell)
        p = cell.paragraphs[0]
        _set_spacing(p, after=40, before=40)
        _run(p, header, size=9, bold=True, color=WHITE)
    for r, row in enumerate(rows):
        fill = ALT_ROW if r % 2 else "FFFFFF"
        for c, value in enumerate(row):
            cell = tbl.rows[r + 1].cells[c]
            cell.text = ""
            shade(cell, fill)
            set_cell_border(cell)
            p = cell.paragraphs[0]
            _set_spacing(p, after=40, before=40)
            _run(p, str(value), size=9, bold=False, color=DARK)
    doc.add_paragraph()
    return tbl


def _setup(doc):
    section = doc.sections[0]
    section.page_width = Twips(12240)
    section.page_height = Twips(15840)
    section.top_margin = Twips(1134)
    section.bottom_margin = Twips(1134)
    section.left_margin = Twips(1247)
    section.right_margin = Twips(1247)
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    style.font.color.rgb = DARK


def _bullets(doc, items):
    for item in items:
        bullet(doc, item)


def _capa_e_resumo(doc):
    cover(doc, "FIAP — Tech Challenge Fase 4", size=24, bold=True, after=120, color=FIAP_RED)
    cover(doc, "Consultório Multimodal com Vídeo, Áudio e Detecção de Anomalias", size=13, bold=True, after=0)
    cover(doc, "+ Azure Cognitive Services", size=13, bold=True, after=80)
    cover(doc, "Tech Challenge — Projeto 4 (Monitoramento Multimodal de Pacientes)", size=11, bold=False, after=80)
    cover(doc, "Grupo:", size=11, bold=True, after=40)
    cover(doc, "Kevin Romeiro Barbosa    RM: 373031", size=11, bold=False, after=80)
    cover(doc, f"Vídeo de apresentação: {VIDEO}", size=11, bold=False, after=80)
    cover(doc, f"GitHub: {REPO}", size=11, bold=False, after=320)

    h1(doc, "1. Resumo Executivo")
    body(
        doc,
        "Este projeto desenvolve um consultório multimodal de suporte à decisão médica,"
        " capaz de acompanhar a consulta e o plantão a partir "
        "de vídeo, áudio, texto e sinais vitais. O objetivo é identificar, em tempo real, situações "
        "que pedem atenção — dor, fala de risco, desvio de postura, sinais vitais fora do padrão, "
        "prescrição de alto alerta — e levar cada achado até a equipe médica em forma de alerta.",
    )
    body(
        doc,
        "O projeto foi desenvolvido em quatro frentes: (1) consulta ao vivo, com transcrição da "
        "conversa pelo Azure Speech, identificação de médico e paciente, pontos de atenção e resumo "
        "clínico; (2) estimativa de dor pelo rosto em cascata — MediaPipe Face no navegador e Py-Feat "
        "no servidor local — apresentada na escala de faces Wong-Baker; (3) exames da internação, com "
        "MediaPipe Pose + YOLOv8n no vídeo e traços vocais + Azure AI Language no áudio; (4) detecção "
        "de anomalias em sinais vitais (Isolation Forest treinado no PhysioNet Challenge 2019), "
        "prescrições e movimentação, com caixa única de alertas para a equipe.",
    )
    body(
        doc,
        "A aplicação web Flask foi organizada em quatro projetos (Domain, Application, "
        "Infrastructure e Web) e conta com 318 testes automatizados. O sistema é de apoio: não "
        "diagnostica, não prescreve e não substitui a avaliação do médico responsável.",
    )


def _instrucoes(doc):
    h1(doc, "2. Instruções de Execução")
    h2(doc, "2.1 Pré-requisitos")
    _bullets(doc, [
        "Python 3.11 ou superior",
        "pip (gerenciador de pacotes Python)",
        "Git",
        "Chrome ou Edge (microfone e câmera só funcionam em localhost ou https)",
        "Webcam e microfone — consulta ao vivo e exame de vídeo",
        "Conta Azure (opcional) — recursos Speech e Language; sem eles as falas podem ser digitadas",
        "Py-Feat (opcional) — estágio 2 da dor, ~1 GB com torch",
    ])

    h2(doc, "2.2 Instalação e Configuração")
    bold_line(doc, "1. Clone o repositório")
    code(doc, f"git clone {REPO}.git")
    code(doc, "cd FIAP_IA_FOR_DEVS_Tech_Challenge_Fase_4")

    bold_line(doc, "2. Crie e ative o ambiente virtual")
    code(doc, "python -m venv .venv")
    code(doc, r"Windows:  .venv\Scripts\Activate.ps1")
    code(doc, "Mac/Linux: source .venv/bin/activate")

    bold_line(doc, "3. Instale as dependências")
    code(doc, "pip install -r requirements.txt")
    code(doc, "# pip install -r requirements-estagio2.txt  # opcional (Py-Feat, estágio 2 da dor)")

    bold_line(doc, "4. Configure o Azure (opcional)")
    code(doc, "copy .env.example .env")
    body(
        doc,
        "Variáveis principais: AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, AZURE_LANGUAGE_KEY e "
        "AZURE_LANGUAGE_ENDPOINT. Sem elas, a transcrição fica desligada e as falas podem ser digitadas. "
        "Opções do estágio 2: ESTAGIO2_DETECTOR (v2|v1), ESTAGIO2_OCIOSIDADE_S (padrão 120) e "
        "ESTAGIO2_DESLIGADO=1.",
        after=80,
    )

    bold_line(doc, "5. Baixe os modelos e gere os dados de demonstração")
    code(doc, "python scripts/download_pose.py")
    code(doc, "python scripts/download_yolo.py")
    code(doc, "python scripts/make_demo_audio.py")
    code(doc, 'python -c "from infrastructure.physionet.challenge2019 import save_choice; save_choice()"')
    code(doc, "python -m infrastructure.persistencia.seed")
    body(
        doc,
        "Os pesos do Py-Feat são baixados automaticamente na primeira confirmação de dor. Para treinar "
        "o modelo de anomalia com a base completa do PhysioNet (~40 mil registros): "
        "python scripts/download_challenge2019.py",
        after=80,
    )

    h2(doc, "2.3 Executando a Aplicação Web")
    bold_line(doc, "Opção A — Via VS Code (recomendado):")
    body(
        doc,
        "Abra a pasta Fase_4 no VS Code e pressione F5 na configuração \"Web: Fase 4 (Flask)\". "
        "A configuração de debug já está em .vscode/launch.json.",
        after=80,
    )
    bold_line(doc, "Opção B — Via terminal:")
    code(doc, "python -m web.app")
    body(
        doc,
        "Acesse http://127.0.0.1:5000 no Chrome ou Edge após iniciar o servidor. O banco SQLite é "
        "criado automaticamente na primeira requisição, junto com as migrações.",
    )

    h2(doc, "2.4 Rotas da Aplicação Web")
    table(
        doc,
        ["Rota", "Descrição"],
        [
            ["/", "Página Hoje — consultas em andamento, alertas que pedem ação e busca de paciente"],
            ["/pacientes", "Busca, cadastro e ficha do paciente com histórico e relatórios"],
            ["/consulta/<id>/preparar", "Etapa 1 — aviso ao paciente e teste de microfone e câmera"],
            ["/consulta/<id>", "Etapa 2 — conversa ao vivo, resumo clínico, câmera e dor Wong-Baker"],
            ["/consulta/<id>/encerrar", "Etapa 3 — revisão, encerramento e relatório para imprimir"],
            ["/revisao", "Marcas de atenção da dor para classificação do médico"],
            ["/internacao", "Painel do internado — exames de vídeo e áudio, achados e monitor"],
            ["/alertas", "Caixa única de alertas — consultas, internação e anomalia de padrão"],
            ["/sistema", "Estado do Azure, Py-Feat e modelos; treino do modelo de anomalia"],
        ],
    )

    h2(doc, "2.5 Consulta ao Vivo (fluxo de uso)")
    _bullets(doc, [
        "Acesse /pacientes, cadastre o paciente e clique em \"Nova consulta\". Na etapa Preparar, teste microfone e câmera e leia o aviso ao paciente.",
        "Clique em \"Iniciar consulta ao vivo\" e em \"Ligar câmera\". A conversa é transcrita e separada entre médico e paciente; os pontos de atenção aparecem destacados na fala.",
        "A dor estimada pelo rosto aparece na escala Wong-Baker. O paciente pode tocar na face que corresponde à sua dor, e as duas leituras ficam gravadas lado a lado.",
        "Os alertas da consulta recebem \"Ciente\" e depois \"Encerrar\". Ao final, clique em \"Encerrar e ver relatório\" para revisar e imprimir.",
    ])

    h2(doc, "2.6 Internação e Plantão (fluxo de uso)")
    _bullets(doc, [
        "Acesse /internacao e selecione p000003 (sinais fora da faixa) ou p000057 (estável), ambos do PhysioNet Challenge 2019.",
        "Em Exames, envie um vídeo ou use a webcam e clique em \"Analisar vídeo\"; para o áudio, clique em \"Usar amostra\" e \"Analisar áudio\".",
        "Em Achados, clique em \"Enviar alertas\" para transformar as anomalias de vitais, prescrição e movimentação em alertas.",
        "Em Monitor, clique em \"Iniciar replay\": a série é reproduzida a 1 ponto por segundo e o alerta dispara no instante em que o sinal sai da faixa.",
    ])

    h2(doc, "2.7 Avaliação Offline")
    body(doc, "Para reproduzir os números da seção 3.10 sem Azure e sem YOLO:")
    code(doc, "python analises/avaliacao_offline.py")
    body(
        doc,
        "O resultado é salvo em hospital_data/fase4/results.json. O Isolation Forest é treinado pela "
        "página Sistema → Anomalia de padrão, clicando em \"Treinar novo modelo\".",
    )

    h2(doc, "2.8 Testes Automatizados")
    code(doc, "python -m pytest")
    code(doc, "python -m pytest tests/unit")
    code(doc, "python -m pytest tests/integration")
    code(doc, "python -m pytest -m azure --azure   # opcional (Azure real)")
    code(doc, "python -m pytest --cov --cov-report=html")
    body(
        doc,
        "Resultado atual: 318 testes aprovados e 5 ignorados (testes com Azure real, executados apenas "
        "com --azure). A suíte cobre domínio e casos de uso com fakes em memória, integração com SQLite, "
        "modelos e rotas, e um teste de arquitetura que impede o domínio de depender da infraestrutura.",
    )


def _dados_e_problemas(doc):
    h1(doc, "3. Relatório Técnico")
    h2(doc, "3.1 Dados — PhysioNet Challenge 2019 e Amostras de Demonstração")
    body(
        doc,
        "Os sinais vitais vêm do PhysioNet Challenge 2019 (Early Prediction of Sepsis from Clinical "
        "Data), base pública com cerca de 40 mil internações em UTI e leituras horárias de sinais "
        "vitais e exames laboratoriais. Para o modelo de anomalia foram usadas quatro variáveis:",
    )
    _bullets(doc, [
        "HR: frequência cardíaca (bpm)",
        "SBP / DBP: pressão arterial sistólica e diastólica (mmHg)",
        "O2Sat: saturação de oxigênio (SpO2, %)",
    ])
    body(
        doc,
        "Dois pacientes foram escolhidos para a demonstração: p000003, com SpO2 e pressão diastólica "
        "fora da faixa, e p000057, estável. O rótulo de sepse da base não é usado no treino, pois o "
        "objetivo é aprender o padrão dos sinais e não prever o desfecho. Prescrição e movimentação "
        "são a evolução clínica do plantão sobre esses mesmos IDs (dados sintéticos), já que a base "
        "não traz essas informações. O áudio de demonstração é fala sintetizada, porque o AudioSet "
        "não contém consultas médicas.",
    )

    h2(doc, "3.2 Diagnóstico de Problemas e Estratégias Adotadas")
    body(doc, "Durante o desenvolvimento foram identificados cinco problemas que mudaram o desenho da solução:")
    bold_line(doc, "Problema 1 — Detecção de emoção do Azure Face descontinuada")
    body(
        doc,
        "A Microsoft retirou a detecção de emoção do Azure Face, o que impede usar o serviço para "
        "estimar dor pelo rosto. Solução: análise facial local, com MediaPipe Face Landmarker no "
        "navegador e Py-Feat no servidor. Como efeito positivo, a imagem do paciente não sai da máquina.",
    )
    bold_line(doc, "Problema 2 — O Azure separa as vozes, mas não diz quem é o médico")
    body(
        doc,
        "O ConversationTranscriber identifica locutores como Guest-1 e Guest-2, sem papel. Solução: "
        "pontuação por fala com base em pistas de linguagem — perguntas e condução apontam para o "
        "médico, relato de sintoma em primeira pessoa aponta para o paciente. A média por locutor "
        "define o papel, e o médico pode corrigir manualmente.",
    )
    bold_line(doc, "Problema 3 — OpenPose não roda no Windows sem compilação")
    body(
        doc,
        "O enunciado cita OpenPose, que exige compilação com CUDA e Caffe. Solução: MediaPipe Pose, "
        "que entrega os mesmos keypoints do corpo, roda em CPU e instala por pip.",
    )
    bold_line(doc, "Problema 4 — Não existe rótulo de dor para definir os limiares")
    body(
        doc,
        "Sem uma base rotulada de dor na consulta, os limiares do PSPI são heurísticos. Solução: cada "
        "suspeita vira uma marca de atenção gravada para revisão do médico, que classifica o recorte. "
        "Assim o próprio uso do sistema produz os rótulos necessários para calibrar os limiares.",
    )
    bold_line(doc, "Problema 5 — Py-Feat é pesado em CPU e memória")
    body(
        doc,
        "Rodar várias confirmações ao mesmo tempo deixaria todas mais lentas e travaria a consulta. "
        "Solução: fila de trabalho em segundo plano que executa uma avaliação por vez, carregamento "
        "sob demanda e liberação do modelo após 120 s sem uso. Sem o Py-Feat instalado, o sistema "
        "segue funcionando apenas com o estágio 1.",
    )

    h2(doc, "3.3 Arquitetura da Solução")
    body(
        doc,
        "A aplicação foi organizada em quatro projetos Python instalados em modo editável, no formato "
        "de uma solution em camadas, em que cada camada só depende das camadas internas:",
    )
    table(
        doc,
        ["Projeto", "Responsabilidade"],
        [
            ["1. Domain", "Agregados e regras clínicas (atendimento, anomalia e plantão) — apenas biblioteca padrão"],
            ["2. Application", "Casos de uso e portas (interfaces de repositório, modelos de IA e Azure)"],
            ["3. Infrastructure", "SQLite, MediaPipe, YOLOv8, Py-Feat, Isolation Forest, Azure e PhysioNet"],
            ["4. Web", "MVC em Flask — controllers, view models, views e composição das dependências (injector)"],
        ],
    )
    body(
        doc,
        "Um teste de arquitetura garante que o domínio não importe Flask, SQLite, numpy ou a "
        "infraestrutura, eliminando o acoplamento entre regra clínica e tecnologia. O banco SQLite "
        "evolui por seis migrações versionadas, cada uma com script de reversão.",
    )


def _modulos(doc):
    h2(doc, "3.4 Consulta ao Vivo — Fala, Interlocutores e Pontos de Atenção")
    body(
        doc,
        "A chave do Azure fica no servidor; o navegador recebe apenas um token temporário para abrir a "
        "transcrição em pt-BR. Cada fala transcrita passa por três etapas:",
    )
    _bullets(doc, [
        "Interlocutor: define se a fala é do médico ou do paciente (Problema 2).",
        "Pontos de atenção: regras clínicas sobre o texto sem acento, com severidade alta ou média — risco à vida, dor torácica, dificuldade respiratória, sinal neurológico, perda de consciência, convulsão, sangramento, alteração cognitiva, falha de adesão e alergia, entre outras. A negação é tratada: \"não tive febre\" não marca febre.",
        "Azure AI Language: sentimento e frases-chave da fala do paciente, complementando as regras.",
    ])
    body(
        doc,
        "Com isso, o resumo clínico reúne queixa principal, tempo de evolução e sintomas para o médico "
        "conferir. O resumo organiza a conversa, mas não sugere diagnóstico.",
    )

    h2(doc, "3.5 Dor Facial em Cascata — Escala Wong-Baker")
    body(
        doc,
        "A estimativa de dor foi construída em cascata: um estágio sensível, que não deixa passar "
        "suspeitas, seguido de um estágio preciso, que só confirma dor moderada. A sensibilidade vem "
        "primeiro, pois deixar de perceber a dor do paciente é clinicamente mais grave do que revisar "
        "uma suspeita a mais.",
    )
    table(
        doc,
        ["Etapa", "Função"],
        [
            ["1. Calibração", "As 5 primeiras leituras definem o rosto neutro do próprio paciente (base limitada a 3.0)"],
            ["2. Estágio 1 — navegador", "MediaPipe Face Landmarker, 52 blendshapes → expressão e PSPI = AU4 + máx(AU6, AU7) + máx(AU9, AU10) + AU43"],
            ["3. Suspeita", "Face Wong-Baker acima de 5 em 3 leituras seguidas → marca de atenção + pedido ao estágio 2"],
            ["4. Estágio 2 — servidor local", "Py-Feat 2.1.5 (detector v2) mede as AUs em 3 recortes; mediana do PSPI menos o rosto neutro"],
            ["5. Confirmação", "Dor relativa ≥ 3.5 confirma e abre o alerta; abaixo disso a suspeita é descartada"],
            ["6. Escala", "Dor relativa → faces Wong-Baker 0, 2, 4, 6, 8 e 10 (faixas < 1, < 2, < 4, < 6, < 9 e ≥ 9)"],
        ],
    )
    body(
        doc,
        "A face que o paciente aponta na tela fica gravada ao lado da estimativa da câmera, permitindo "
        "medir a concordância entre as duas. Além do rosto, a dor pode abrir alerta pelo relato (ex.: "
        "\"pontada\") ou pela movimentação (ex.: \"mancando\"). Todo alerta passa por aberto → ciente → "
        "encerrado e só sai da tela quando o médico encerra.",
    )

    h2(doc, "3.6 Revisão das Marcas de Atenção")
    body(
        doc,
        "Cada suspeita do estágio 1 é gravada na hora como um recorte de 2 a 4 segundos (2 s antes e "
        "2 s depois do momento da suspeita), armazenado apenas no computador local. O veredito do "
        "estágio 2 chega depois — confirmada, descartada ou sem resultado — e serve apenas de apoio; "
        "marcas perto do limiar (±1.0) são destacadas.",
    )
    body(
        doc,
        "Na tela /revisao o médico assiste ao recorte em loop e registra a face Wong-Baker real, uma "
        "categoria (dor, sem dor, outra expressão ou imagem ruim) e uma observação. Cada classificação "
        "vira um exemplo rotulado para calibrar os limiares (Problema 4).",
    )

    h2(doc, "3.7 Vídeo e Áudio da Internação")
    bold_line(doc, "Vídeo")
    body(
        doc,
        "O vídeo é lido com OpenCV e cada quadro passa pelo MediaPipe Pose. O ângulo de abdução do "
        "ombro é calculado com ombro, cotovelo e quadril e comparado ao alvo do exercício (ex.: "
        "shoulder_abduction, alvo de 90°). Em paralelo, o YOLOv8n detecta objetos no quadro, e as "
        "zonas classificam o evento como objeto no campo crítico ou fora da área segura. O relatório "
        "final resume os desvios de postura e os eventos de zona.",
    )
    bold_line(doc, "Áudio")
    _bullets(doc, [
        "Transcrição: Azure Speech to Text.",
        "Sentimento e frases-chave: Azure AI Language.",
        "Termos críticos: falta de ar, cansaço, dor no peito, desmaio, sangramento e confusão.",
        "Fadiga: razão de pausa acima de 40% (janelas de 30 ms).",
        "Esforço respiratório: fadiga com energia de fala baixa (RMS < 0.05).",
    ])
    body(doc, "Os traços vocais indicam alteração na voz, não um diagnóstico respiratório.")

    h2(doc, "3.8 Detecção de Anomalias")
    table(
        doc,
        ["Dado", "Método", "Critério", "Obs."],
        [
            ["Sinais vitais", "Regras", "SpO2 ≥ 92 · FC 45–120 · PAS 90–180 · PAD 50–110", "Disparo imediato no monitor"],
            ["Sinais vitais", "Z-score", "|z| ≥ 3 a partir de 24 leituras", "Outlier da própria série"],
            ["Sinais vitais", "Isolation Forest", "80 árvores, contaminação 5%, random_state=0", "Modelo treinado"],
            ["Prescrição", "Regras", "Início de droga de alto alerta; dose ≥ 2× a anterior", "Ex.: varfarina, AAS"],
            ["Movimentação", "Regras", "Imobilidade ≥ 4 h; saída noturna (22 h–5 h)", "Ex.: corredor"],
        ],
    )
    body(
        doc,
        "O Isolation Forest é treinado com até 8 mil leituras horárias de FC, PAS, PAD e SpO2 do "
        "PhysioNet (mínimo de 24). Para explicar o resultado, calcula-se a média do z-score nos pontos "
        "anômalos, e os sinais com z ≥ 2 são nomeados (batimentos, pressão arterial ou oxigenação). "
        "Uma detecção apenas por faixa fixa é recusada pelo domínio, pois o requisito pede um modelo "
        "treinado.",
    )

    h2(doc, "3.9 Fusão, Alertas e Monitoramento em Tempo Real")
    body(
        doc,
        "Na consulta, fala, rosto e movimentação aparecem na mesma tela, e qualquer uma das origens "
        "basta para abrir o alerta. No plantão, os achados de vídeo, áudio, vitais, prescrição e "
        "movimentação são consolidados em um nível único de severidade, sempre com prescribes = false.",
    )
    body(
        doc,
        "Todos os alertas chegam à caixa única /alertas, separados por origem (consultas, internação e "
        "anomalia de padrão), onde o médico dá ciência e encerra. O tempo real foi tratado em duas "
        "frentes: a consulta ao vivo, com transcrição contínua e leitura da câmera, e o monitor da "
        "internação, que reproduz a série a 1 ponto por segundo e dispara o alerta no instante em que "
        "o sinal sai da faixa.",
    )


def _resultados(doc):
    h2(doc, "3.10 Resultados e Discussão Crítica")
    body(
        doc,
        "Os detectores foram avaliados com analises/avaliacao_offline.py sobre casos controlados — sem "
        "Azure e sem YOLO — e com as séries PhysioNet dos dois pacientes de demonstração:",
    )
    table(
        doc,
        ["Modalidade", "Caso de teste", "Resultado"],
        [
            ["Vídeo — postura", "Abdução do ombro, alvo 90°", "Desvio detectado: abdução de 180°"],
            ["Vídeo — área crítica", "Celular no quadro", "Objeto dentro do campo crítico"],
            ["Áudio — voz", "Sinal sintético com pausas", "Razão de pausa 0.48 → fadiga"],
            ["Áudio — texto", "Amostra sintetizada", "Termo crítico \"falta de ar\" + sentimento negativo"],
            ["Sinais vitais", "Leitura do plantão", "SpO2 88% e FC 132 bpm — severidade alta"],
            ["Prescrição", "Evolução do plantão", "Início de varfarina; AAS de 100 mg para 300 mg"],
            ["Movimentação", "Evolução do plantão", "Imobilidade de 8 h; saída noturna no corredor"],
            ["Fusão", "Todos os achados", "Nível alto, 10 achados, nenhuma prescrição"],
        ],
    )
    table(
        doc,
        ["Paciente", "Isolation Forest", "Sinais apontados"],
        [
            ["p000003", "Anômalo", "Oxigenação e pressão arterial"],
            ["p000057", "Compatível com o padrão", "—"],
        ],
    )
    bold_line(doc, "Modalidades: 5  |  Achados na fusão: 10  |  Testes: 318 aprovados")
    body(
        doc,
        "Todos os casos controlados foram detectados, e cada achado chegou até uma ação do médico na "
        "caixa de alertas. Esses números são verificações funcionais, não métricas de acurácia em "
        "população, pois não existe rótulo clínico de dor ou de evento adverso para os pacientes de "
        "demonstração. Por esse motivo a revisão das marcas de atenção foi incluída: ela transforma o "
        "uso do sistema em dados rotulados para medir e calibrar a cascata.",
    )

    h3(doc, "Pontos Fortes")
    _bullets(doc, [
        "Cobertura de todas as modalidades — vídeo, áudio, vitais, prescrição, movimentação, fusão, tempo real e alerta",
        "Cascata de dor local — imagem do paciente não sai da máquina e só a confirmação abre alerta",
        "Sensibilidade priorizada — toda suspeita é gravada para o médico, mesmo quando o validador descarta",
        "Modelo de anomalia treinado em dados reais (PhysioNet) — detecção por faixa fixa é recusada",
        "Azure Speech e Azure AI Language integrados, com fallback digitado quando não há chave",
        "318 testes automatizados e teste de arquitetura — domínio isolado da infraestrutura",
        "Caminho completo do alerta — do sinal até a ciência e o encerramento pelo médico",
    ])

    h3(doc, "Limitações")
    _bullets(doc, [
        "Limiares de dor heurísticos — dependem das marcas revisadas para serem calibrados",
        "Wong-Baker é escala de autorrelato — a estimativa da câmera é observacional, não escore validado",
        "Identificação de médico e paciente por padrões de fala — pode errar e exige correção manual",
        "Prescrição e movimentação sintéticas — a base PhysioNet não traz essas informações",
        "Avaliação em casos controlados — sem métrica de acurácia populacional",
        "Dependência de internet na primeira carga (MediaPipe Face via CDN) e de chave própria do Azure",
    ])

    h3(doc, "Trabalhos Futuros")
    _bullets(doc, [
        "Calibrar os limiares da cascata com as marcas classificadas pelo médico (curva ROC)",
        "Medir a concordância entre a face apontada pelo paciente e a estimativa da câmera",
        "Treinar o modelo de anomalia com janelas temporais (tendência) além de leituras isoladas",
        "Integrar com prontuário eletrônico e enviar notificação ativa à equipe",
        "Persistir métricas e trilha de auditoria das ações sobre os alertas",
    ])


def _anexos(doc):
    h1(doc, "4. Estrutura do Projeto")
    body(doc, "O projeto segue arquitetura em quatro projetos e está organizado em módulos independentes:")
    table(
        doc,
        ["Pasta / Arquivo", "Conteúdo"],
        [
            ["src/Domain/", "Agregados e regras — atendimento, anomalia e plantão"],
            ["src/Application/", "Casos de uso e portas"],
            ["src/Infrastructure/", "Persistência, modelos de IA, Azure e PhysioNet"],
            ["src/Web/", "Aplicação Flask MVC (controllers, models, views, static)"],
            ["tests/", "Testes unitários, de integração e de arquitetura"],
            ["scripts/", "Download de modelos e da base PhysioNet; áudio de demonstração"],
            ["analises/", "Avaliação offline e notebooks"],
            ["docs/", "Relatório técnico, gerador do Word e roteiro do vídeo"],
            ["hospital_data/", "Banco SQLite, registros PhysioNet e recortes das marcas de atenção"],
            ["models/", "Pesos baixados — pose, YOLO e Py-Feat (fora do Git)"],
            ["requirements.txt", "Dependências da aplicação e dos testes"],
            ["requirements-estagio2.txt", "Dependência opcional do estágio 2 (Py-Feat)"],
            ["README.md", "Guia de execução e visão geral"],
        ],
    )

    h1(doc, "5. Dependências Principais")
    table(
        doc,
        ["Biblioteca", "Uso no Projeto"],
        [
            ["Flask", "Servidor web WSGI / MVC"],
            ["injector / python-dotenv", "Injeção de dependências e configuração (.env)"],
            ["Azure Speech", "Transcrição da conversa com separação de vozes"],
            ["Azure AI Language", "Sentimento e frases-chave (Text Analytics)"],
            ["mediapipe", "Pose (corpo) no servidor e Face Landmarker (rosto) no navegador"],
            ["ultralytics", "YOLOv8n — objetos e áreas críticas"],
            ["py-feat (opcional)", "Unidades de ação faciais no estágio 2 da dor"],
            ["scikit-learn", "Isolation Forest"],
            ["opencv-python / numpy", "Leitura de vídeo e traços vocais"],
            ["requests", "Chamadas ao Azure e downloads"],
            ["pytest / pytest-cov", "Testes automatizados e cobertura"],
            ["python-docx", "Geração deste relatório Word"],
        ],
    )

    h1(doc, "6. Links de Entrega")
    table(
        doc,
        ["Entregável", "URL"],
        [
            ["Código-fonte (GitHub)", REPO],
            ["Dataset (PhysioNet Challenge 2019)", "https://physionet.org/content/challenge-2019/1.0.0/"],
        ],
    )

    p = doc.add_paragraph()
    _set_spacing(p, after=80, before=160)
    _run(
        p,
        "Aviso: uso educacional. O sistema auxilia a consulta e o plantão, mas não substitui a avaliação "
        "médica, não emite prescrição e não confirma diagnóstico. Dados PhysioNet e sintéticos — não "
        "usar com paciente real.",
        size=11,
        bold=False,
        color=DARK,
    )


def build() -> Path:
    doc = Document()
    _setup(doc)
    _capa_e_resumo(doc)
    _instrucoes(doc)
    _dados_e_problemas(doc)
    _modulos(doc)
    _resultados(doc)
    _anexos(doc)
    doc.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print("wrote", path)
