"""Pontos de interesse clínico no texto da fala: medicamentos, doenças, exames, dose, hábitos...

Extração por dicionário e padrões em português (sem rede, em milissegundos), para marcar
na conversa tudo que o médico costuma anotar. Não diagnostica: só aponta o que foi dito.
Menção negada ("não tenho diabetes") também é informação e vem marcada como negada.
"""
from __future__ import annotations

import re

from domain.atendimento.conversa.atencao import _NEGACAO, _sem_acento

MEDICAMENTO = "Medicamento"
POSOLOGIA = "Dose / posologia"
DOENCA = "Doença / condição"
SINTOMA = "Sintoma"
EXAME = "Exame"
MEDIDA = "Medida relatada"
ALERGIA = "Alergia"
HABITO = "Hábito"
FAMILIAR = "Histórico familiar"
CIRURGIA = "Cirurgia / procedimento"
CORPO = "Parte do corpo"
TEMPO = "Tempo / evolução"

# Ordem de exibição no resumo.
TIPOS = (MEDICAMENTO, POSOLOGIA, ALERGIA, DOENCA, SINTOMA, CORPO, TEMPO, MEDIDA, EXAME,
         FAMILIAR, CIRURGIA, HABITO)


def _palavras(*termos: str) -> str:
    """Alternativa de termos inteiros, o mais longo primeiro (para 'pressao alta' vencer 'pressao')."""
    return r"\b(?:" + "|".join(sorted(termos, key=len, reverse=True)) + r")\b"


_MEDICAMENTOS = _palavras(
    # cardiovascular
    "losartana", "losartan", "valsartana", "olmesartana", "candesartana", "enalapril", "captopril", "lisinopril",
    "ramipril", "anlodipino", "nifedipino", "hidroclorotiazida", "clortalidona", "furosemida", "espironolactona",
    "indapamida", "atenolol", "propranolol", "metoprolol", "carvedilol", "bisoprolol", "nebivolol",
    "sinvastatina", "atorvastatina", "rosuvastatina", "pravastatina", "ezetimiba", "digoxina", "amiodarona",
    "isossorbida", "monocordil", "sustrate", "aas", "aspirina", r"acido acetilsalicilico", "clopidogrel",
    "varfarina", "marevan", "rivaroxabana", "xarelto", "apixabana", "eliquis", "dabigatrana", "heparina",
    "enoxaparina", "clexane",
    # metabólico / endócrino
    "metformina", "glifage", "glibenclamida", "gliclazida", "glimepirida", "sitagliptina", "januvia",
    "dapagliflozina", "forxiga", "empagliflozina", "jardiance", "insulina", "nph", "ozempic", "semaglutida",
    "levotiroxina", "puran", "euthyrox", "synthroid",
    # dor / anti-inflamatório
    "dipirona", "novalgina", "paracetamol", "tylenol", "ibuprofeno", "advil", "alivium", "nimesulida",
    "diclofenaco", "cataflam", "voltaren", "cetoprofeno", "profenid", "naproxeno", "meloxicam", "celecoxibe",
    "tramadol", "tramal", "codeina", "tylex", "morfina", "dorflex", "neosaldina", "buscopan", "escopolamina",
    "torsilax", "miosan", "ciclobenzaprina",
    # antibiótico / antiviral
    "amoxicilina", "clavulanato", "azitromicina", "claritromicina", "cefalexina", "ceftriaxona",
    "ciprofloxacino", "levofloxacino", "sulfametoxazol", "bactrim", "nitrofurantoina", "metronidazol",
    "doxiciclina", "penicilina", "benzetacil", "oseltamivir", "tamiflu", "aciclovir", "ivermectina",
    "albendazol",
    # respiratório / alergia
    "salbutamol", "aerolin", "budesonida", "formoterol", "alenia", "seretide", "symbicort", "beclometasona",
    "montelucaste", "loratadina", "desloratadina", "cetirizina", "fexofenadina", "allegra", "dexclorfeniramina",
    "polaramine", "prometazina", "fenergan", "prednisona", "prednisolona", "dexametasona", "hidrocortisona",
    "betametasona", "celestone",
    # gastro
    "omeprazol", "pantoprazol", "esomeprazol", "lansoprazol", "ranitidina", "domperidona", "metoclopramida",
    "plasil", "ondansetrona", "vonau", "dramin", "simeticona", "luftal", "lactulose", "loperamida",
    "hioscina",
    # sistema nervoso
    "fluoxetina", "sertralina", "escitalopram", "citalopram", "paroxetina", "venlafaxina", "desvenlafaxina",
    "duloxetina", "bupropiona", "amitriptilina", "nortriptilina", "clonazepam", "rivotril", "diazepam",
    "valium", "alprazolam", "lorazepam", "zolpidem", "quetiapina", "risperidona", "olanzapina",
    "haloperidol", "carbamazepina", "valproato", "depakote", "lamotrigina", "topiramato", "gabapentina",
    "pregabalina", "lyrica", "fenitoina", "fenobarbital", "gardenal", "litio", "levodopa", "donepezila",
    "metilfenidato", "ritalina",
    # outros
    "anticoncepcional", "pilula", "vitamina d", "vitamina b12", r"sulfato ferroso", r"acido folico", "alopurinol",
    "colchicina", "finasterida", "tansulosina", "sildenafila", "viagra", "metotrexato", "hidroxicloroquina",
)
# Sufixos de classe farmacológica pegam o que o dicionário não tem.
_SUFIXO_REMEDIO = r"\b\w{3,}(?:pril|sartana|olol|statina|prazol|micina|cilina|oxacino|azepam|tidina|dipino|gliptina|gliflozina|triptana)\b"

_DOENCAS = _palavras(
    "hipertensao", "hipertenso", "hipertensa", r"pressao alta", r"pressao baixa", "hipotensao", "diabetes",
    "diabetico", "diabetica", r"acucar alto", r"pre-diabetes", "asma", "asmatico", "asmatica", "bronquite",
    "dpoc", "enfisema", "pneumonia", "covid", "covid-19", "coronavirus", "gripe", "resfriado", "sinusite",
    "rinite", "amigdalite", "faringite", "otite", "infarto", "enfarte", "avc", "derrame", "isquemia", "angina",
    "arritmia", r"fibrilacao atrial", r"insuficiencia cardiaca", r"sopro no coracao", r"colesterol alto",
    "colesterol", "triglicerides", "dislipidemia", "hipotireoidismo", "hipertireoidismo", "tireoide", "cancer",
    "tumor", "leucemia", "linfoma", "depressao", "ansiedade", r"sindrome do panico", r"panico",
    r"transtorno bipolar", "bipolar", "esquizofrenia", "enxaqueca", "gastrite", "refluxo", "ulcera", "hepatite",
    "cirrose", r"esteatose", r"gordura no figado", r"insuficiencia renal", r"pedra no rim", r"calculo renal",
    r"infeccao urinaria", "cistite", "dengue", "zika", "chikungunya", "tuberculose", "hiv", "aids", "sifilis",
    "artrite", "artrose", "osteoporose", "epilepsia", "obesidade", "anemia", "trombose", "embolia",
    "alzheimer", "demencia", "parkinson", "labirintite", "lupus", "fibromialgia", "hernia", "gota", "psoriase",
    "dermatite", "apneia", "glaucoma", "catarata", "endometriose", r"ovario policistico", "mioma",
    "hemorroida", "varizes", "celulite infecciosa", "erisipela", "conjuntivite", "virose", "infeccao",
    "covid longa", "autismo", "tdah", "insonia",
)

_SINTOMAS = _palavras(
    r"dor de cabeca", r"dores de cabeca", "cefaleia", r"dor de garganta", r"dor de barriga", r"dor nas costas",
    r"dor no corpo", r"dores no corpo", "dor", "dores", "febre", "calafrio", "calafrios", "tosse", "catarro",
    "secrecao", "coriza", r"nariz entupido", "espirro", "espirros", r"falta de ar", "chiado", "palpitacao",
    "palpitacoes", r"coracao acelerado", "taquicardia", "tontura", "tonturas", "vertigem", "desmaio", "nausea",
    "nauseas", "enjoo", "enjoada", "enjoado", "vomito", "vomitos", "vomitando", "diarreia", r"prisao de ventre",
    "constipacao", "azia", "queimacao", "inchaco", "inchado", "inchada", "inchados", "inchadas", "coceira",
    "manchas", "mancha", "ferida", "feridas", "formigamento", "dormencia", "fraqueza", "cansaco", "cansada",
    "cansado", "fadiga", r"perda de peso", r"perdi peso", r"ganho de peso", r"falta de apetite", r"sem apetite",
    r"sem fome", r"suor noturno", "sudorese", "suando", r"visao turva", r"vista embacada", "zumbido",
    r"ardencia ao urinar", r"ardor ao urinar", r"sangue na urina", "sangramento", "rouquidao", "tremor",
    "tremores", "convulsao", "confusao", r"perda de memoria", "esquecimento", "tristeza", "desanimo",
    r"sem dormir", r"nao consigo dormir", "insonia", "pontada", "pontadas", "colica", "colicas",
)

_EXAMES = _palavras(
    "hemograma", r"exame de sangue", r"exames de sangue", r"exame de urina", r"exame de fezes", "urina tipo 1",
    "eletrocardiograma", "ecg", "ecocardiograma", "holter", r"teste ergometrico", "cateterismo",
    r"raio-x", r"raio x", r"raios x", "radiografia", "tomografia", "ressonancia", "ultrassom", "ultrassonografia",
    "ecografia", "endoscopia", "colonoscopia", "mamografia", "papanicolau", "biopsia", "psa", "tsh", "t4",
    "glicemia", r"hemoglobina glicada", "creatinina", "ureia", "tgo", "tgp", "pcr", "d-dimero", "troponina",
    "espirometria", "eletroencefalograma", "densitometria", r"teste rapido", r"teste de covid", "sorologia",
    "gasometria", "lipidograma",
)

_CORPO = _palavras(
    "cabeca", "testa", "nuca", "olho", "olhos", "ouvido", "ouvidos", "nariz", "boca", "garganta", "dente",
    "dentes", "pescoco", "ombro", "ombros", "braco", "bracos", "cotovelo", "punho", "mao", "maos", "dedo",
    "dedos", "peito", "torax", "costas", "coluna", "lombar", "costela", "costelas", "barriga", "abdomen",
    "estomago", "figado", "rim", "rins", "bexiga", "virilha", "quadril", "bacia", "perna", "pernas", "coxa",
    "joelho", "joelhos", "panturrilha", "tornozelo", "pe", "pes", "calcanhar", "pele", "coracao", "pulmao",
    "pulmoes", "utero", "seio", "seios", "mama", "mamas", "prostata",
)

# "dor no peito", "inchaço nas pernas": sintoma com o local num trecho só.
_SINTOMA_LOCAL = (
    r"\b(?:dor|dores|pontadas?|inchaco|coceira|formigamento|dormencia|queimacao|ardencia|manchas?|caroco)"
    r"\s+(?:no|na|nos|nas|em|do|da|de|atras do|atras da)\s+(?:meu |minha |meus |minhas )?" + _CORPO[2:-2] + r"\b"
)

_POSOLOGIA = (
    r"\b\d+(?:[.,]\d+)?\s*(?:mg|miligramas?|mcg|g|gramas?|ml|ui|unidades|gotas)\b",
    r"\b(?:\d+|um|uma|dois|duas|tres|meio|meia)\s+(?:comprimidos?|capsulas?|gotas|colheres?|doses?|jatos?|puffs?|ampolas?)\b",
    r"\b(?:de|a cada)\s+\d+\s+(?:em\s+\d+\s+)?horas\b",
    r"\b(?:uma|duas|tres|quatro|\d+)\s+vez(?:es)?\s+(?:ao|por|no)\s+dia\b",
    r"\b(?:de|pela|a) (?:manha|noite|tarde)\b(?: e (?:a|de) (?:manha|noite|tarde))?",
    r"\bem jejum\b|\bantes de dormir\b|\bdepois do almoco\b|\bantes do cafe\b|\bquando (?:tenho|sinto|da) dor\b",
)

_MEDIDAS = (
    r"\bpressao\s+(?:esta |estava |deu |de |ficou |foi |a )?\d{2,3}\s*(?:por|x|/)\s*\d{1,3}\b",
    # "estava 16 por 10" sem a palavra pressão (ela pode estar na pergunta do médico)
    r"\b(?:[89]|1\d|2[0-4]|[89]\d|1\d\d|2[0-4]\d)\s*(?:por|x)\s*(?:[5-9]|1[0-4]|[4-9]\d|1[0-4]\d)\b(?!\s*(?:dias?|horas?|vez))",
    r"\b(?:febre de |temperatura de |deu |termometro marcou )?\d{2}(?:[.,]\d)?\s*(?:graus|ºc|°c)\b",
    r"\b(?:glicemia|glicose|acucar|dextro|hgt)\s+(?:esta |estava |deu |de |em |a )?\d{2,3}\b",
    r"\b(?:saturacao|oxigenacao)\s+(?:esta |estava |deu |de |em |a )?\d{2}\s*%?",
    r"\b(?:peso|pesando|peso de)\s+\d{2,3}(?:[.,]\d)?\s*(?:kg|quilos?)?\b",
    r"\b(?:batimentos?|frequencia|pulso)\s+(?:esta |estava |deu |de |em |a )?\d{2,3}\b",
    r"\b(?:[0-9]|10)\s*(?:de|em)\s*10\b",
)

_TEMPO = (
    r"(?:\bha|\bfaz|desde ha)\s+(?:uns\s+|umas\s+|mais de\s+|quase\s+)?(?:\d+|um|uma|dois|duas|tres|quatro|cinco|seis"
    r"|sete|oito|nove|dez|alguns|algumas|muitos|muitas|pouco|poucos|poucas)\s+(?:horas?|dias?|semanas?|mes|meses|anos?)\b",
    r"\bdesde (?:ontem|anteontem|a semana passada|semana passada|o mes passado|mes passado|o ano passado|crianca|sempre"
    r"|segunda|terca|quarta|quinta|sexta|sabado|domingo|janeiro|fevereiro|marco|abril|maio|junho|julho|agosto"
    r"|setembro|outubro|novembro|dezembro)\b",
    r"\b(?:hoje de manha|ontem a noite|essa semana|esta semana|essa noite|de repente|toda noite|todo dia|todos os dias)\b",
)

_HABITOS = (
    r"\b(?:fumo|fumante|fumei|fumava|parei de fumar|cigarros?|tabagismo|tabagista|cigarro eletronico|vape|narguile)\b",
    r"\b(?:bebo|bebia|bebida alcoolica|bebidas alcoolicas|alcool|cerveja|cachaca|vinho|etilista|etilismo)\b",
    r"\b(?:maconha|cocaina|crack|drogas)\b",
    r"\b(?:sedentari[oa]|sedentarismo|academia|caminhada|caminho todo dia|corro|faco exercicio|atividade fisica|musculacao)\b",
)

_FAMILIA = (
    r"\b(?:minha|meu)\s+(?:mae|pai|irmao|irma|avo|tio|tia|filho|filha|primo|prima)\b"
    r"(?:\s+\w+){0,3}?\s+(?:tem|teve|tinha|morreu de|faleceu de|sofre de|e|era)\b(?:\s+\w+){1,3}",
    r"\b(?:historico|historia|caso) (?:de \w+ )?na familia\b|\bna (?:minha )?familia (?:tem|teve|todo mundo tem)\b(?:\s+\w+){1,2}",
)

_CIRURGIA = (
    r"\b(?:operei|fui operad[oa]|(?:fiz (?:uma )?)?cirurgia(?: (?:de|do|da|no|na) \w+)?"
    r"|operacao (?:de|do|da) \w+|internad[oa]|internacao|fiz (?:um )?cateterismo|coloquei (?:um )?(?:stent|marcapasso)"
    r"|stent|marcapasso|ponte de safena|transplante)\b",
)

_ALERGIA = r"\b(?:alergia|alergico|alergica|alergicos)\s+(?:a|ao|a|as|aos|de|com)\s+((?:\w+-?)+(?:\s+(?:de|a)\s+\w+)?)"


def _compilar(tipo: str, padroes) -> list[tuple[str, re.Pattern]]:
    if isinstance(padroes, str):
        padroes = (padroes,)
    return [(tipo, re.compile(p)) for p in padroes]


# Mais específico primeiro: quem marca um trecho antes impede a sobreposição.
_REGRAS: list[tuple[str, re.Pattern]] = (
    _compilar(FAMILIAR, _FAMILIA)
    + _compilar(MEDIDA, _MEDIDAS)
    + _compilar(POSOLOGIA, _POSOLOGIA)
    + _compilar(MEDICAMENTO, (_MEDICAMENTOS, _SUFIXO_REMEDIO))
    + _compilar(EXAME, _EXAMES)
    + _compilar(DOENCA, _DOENCAS)
    + _compilar(SINTOMA, (_SINTOMA_LOCAL, _SINTOMAS))
    + _compilar(TEMPO, _TEMPO)
    + _compilar(CIRURGIA, _CIRURGIA)
    + _compilar(HABITO, _HABITOS)
    + _compilar(CORPO, _CORPO)
)
_ALERGIA_RE = re.compile(_ALERGIA)
# Tipos em que "não" muda o sentido (não tenho diabetes, não fumo) e vale anotar como negado.
_NEGAVEIS = {DOENCA, SINTOMA, ALERGIA, HABITO, MEDICAMENTO, CIRURGIA}
# "sem" antes de doença/sintoma nega; antes de remédio ("sem tomar losartana") também.
_ENTRE_SIM_NAO = re.compile(r"\b(?:nao|nunca|nem|sem|nenhuma?|jamais)\b")


def _negada(normal: str, inicio: int) -> bool:
    janela = normal[max(0, inicio - 30):inicio]
    if not _NEGACAO.search(janela):
        return False
    # "não, mas tenho diabetes": a vírgula/ponto encerra a negação
    ultimo = list(_ENTRE_SIM_NAO.finditer(janela))[-1]
    return not re.search(r"[,.;!?]|\bmas\b", janela[ultimo.end():])


def extrair_entidades(texto: str) -> list[dict]:
    """[{tipo, texto, normal, inicio, fim, negada}] na ordem do texto."""
    normal = _sem_acento(texto)
    achados: list[dict] = []
    ocupados: list[tuple[int, int]] = []

    def _livre(ini: int, fim: int) -> bool:
        return not any(ini < b and a < fim for a, b in ocupados)

    def _guardar(tipo: str, ini: int, fim: int, inicio_frase: int | None = None) -> None:
        negada = tipo in _NEGAVEIS and _negada(normal, ini if inicio_frase is None else inicio_frase)
        trecho = texto[ini:fim].strip(" ,.;")
        if not trecho:
            return
        ini = texto.index(trecho, ini)
        fim = ini + len(trecho)
        achados.append({
            "tipo": tipo,
            "texto": trecho,
            "normal": normal[ini:fim],
            "inicio": ini,
            "fim": fim,
            "negada": negada,
        })
        ocupados.append((ini, fim))

    for match in _ALERGIA_RE.finditer(normal):
        ini, fim = match.span(1)
        if _livre(ini, fim):
            _guardar(ALERGIA, ini, fim, inicio_frase=match.start())  # "nunca tive alergia a X"
    for tipo, padrao in _REGRAS:
        for match in padrao.finditer(normal):
            ini, fim = match.span()
            if fim > ini and _livre(ini, fim):
                _guardar(tipo, ini, fim)
    achados.sort(key=lambda item: item["inicio"])
    return achados


def resumo(entidades: list[dict]) -> list[dict]:
    """Agrupa por tipo, sem repetir o termo: [{tipo, itens: [{texto, negada, vezes, falas, medico}]}].

    `medico` fica verdadeiro só quando todas as menções vieram do médico (conduta, não relato).
    """
    grupos: dict[str, dict[tuple[str, bool], dict]] = {}
    for ent in entidades:
        chave = (ent["normal"], bool(ent["negada"]))
        grupo = grupos.setdefault(ent["tipo"], {})
        item = grupo.setdefault(chave, {"texto": ent["texto"], "negada": bool(ent["negada"]), "vezes": 0,
                                        "falas": [], "medico": True})
        item["vezes"] += 1
        item["medico"] = item["medico"] and bool(ent.get("medico"))
        if ent.get("ordem") is not None and ent["ordem"] not in item["falas"]:
            item["falas"].append(ent["ordem"])
    saida = []
    for tipo in TIPOS:
        if tipo not in grupos:
            continue
        chaves = list(grupos[tipo])
        # "dor" some quando já há "dor no peito": o específico cobre o genérico
        itens = [grupos[tipo][(normal, neg)] for normal, neg in chaves
                 if not any(neg == n2 and normal != o2 and re.search(r"\b" + re.escape(normal) + r"\b", o2)
                            for o2, n2 in chaves)]
        saida.append({"tipo": tipo, "itens": itens})
    return saida
