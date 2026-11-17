"""Repositórios do Atendimento em memória: implementam os Protocols de domain/atendimento/repositorios.py."""
from __future__ import annotations

from dataclasses import dataclass, field

from application.atendimento.servico_cadastro import ServicoCadastro
from application.atendimento.servico_camera import ServicoCamera
from application.atendimento.servico_cascata import ServicoCascataDor
from application.atendimento.servico_consulta import ServicoConsulta
from application.atendimento.servico_conversa import ServicoConversa
from application.atendimento.servico_duvidas import ServicoDuvidas
from application.atendimento.servico_validacao import ServicoValidacaoDeMarcas
from tests.fakes import IdsSequenciais, RelogioFixo, UnidadeDeTrabalhoFalsa


class PorId:
    def __init__(self):
        self.itens = {}

    def adicionar(self, item):
        self.itens[item.id] = item

    def obter(self, item_id):
        return self.itens.get(item_id)

    def salvar(self, item):
        self.itens[item.id] = item

    def listar(self):
        return sorted(self.itens.values(), key=lambda p: (p.nome, p.id))


class Sessoes(PorId):
    def do_paciente(self, paciente_id):
        return sorted((s for s in self.itens.values() if s.paciente_id == paciente_id),
                      key=lambda s: s.iniciada_em, reverse=True)

    def em_andamento(self):
        return sorted((s for s in self.itens.values() if s.em_andamento), key=lambda s: s.iniciada_em)


class Alertas(PorId):
    def da_sessao(self, sessao_id):
        return [a for a in self.itens.values() if a.sessao_id == sessao_id]

    def ativos(self):
        return sorted((a for a in self.itens.values() if a.ativo), key=lambda a: a.criado_em)


class PorSessao:
    def __init__(self):
        self.itens: dict[str, list[dict]] = {}

    def adicionar(self, sessao_id, item):
        self.itens.setdefault(sessao_id, []).append(dict(item))

    def _lista(self, sessao_id):
        return self.itens.get(sessao_id, [])


class Leituras(PorSessao):
    def pspi_iniciais(self, sessao_id, limite):
        return [l["dor_pspi"] for l in self._lista(sessao_id)[:limite]]

    def recentes(self, sessao_id, limite):
        return [{"expressao": l["expressao"], "nivel_dor": l["nivel_dor"], "wong_baker": l["wong_baker"]}
                for l in reversed(self._lista(sessao_id))][:limite]

    def ultima(self, sessao_id):
        lista = self._lista(sessao_id)
        return dict(lista[-1]) if lista else None


class Eventos(PorSessao):
    def ultima_expressao(self, sessao_id):
        expressoes = [e["expressao"] for e in self._lista(sessao_id) if e["tipo"] == "expressao"]
        return expressoes[-1] if expressoes else None

    def da_sessao(self, sessao_id):
        return list(self._lista(sessao_id))


class Confirmacoes(PorSessao):
    def ultima(self, sessao_id):
        lista = self._lista(sessao_id)
        return dict(lista[-1]) if lista else None

    def obter(self, confirmacao_id):
        for sessao_id, lista in self.itens.items():
            for c in lista:
                if c["id"] == confirmacao_id:
                    return {**c, "sessao_id": sessao_id}
        return None


class Duvidas(PorId):
    def listar(self, pendentes=None):
        itens = sorted(self.itens.values(), key=lambda d: d.criado_em, reverse=True)
        return [d for d in itens if pendentes is None or d.pendente == pendentes]


class ArmazemFalso:
    def __init__(self):
        self.quadros = {}

    def guardar(self, duvida_id, quadros):
        self.quadros[duvida_id] = list(quadros)

    def ler(self, duvida_id, indice):
        lista = self.quadros.get(duvida_id, [])
        return lista[indice] if 0 <= indice < len(lista) else None


class Conversa:
    def __init__(self):
        self.falas_, self.pontos_, self.locutores_ = {}, {}, {}

    def proxima_ordem(self, sessao_id):
        return len(self.falas_.get(sessao_id, [])) + 1

    def adicionar_fala(self, sessao_id, fala):
        self.falas_.setdefault(sessao_id, []).append(dict(fala))

    def adicionar_ponto(self, sessao_id, ponto):
        self.pontos_.setdefault(sessao_id, []).append(dict(ponto))

    def falas(self, sessao_id):
        return [dict(f) for f in self.falas_.get(sessao_id, [])]

    def pontos(self, sessao_id):
        ordem = {f["id"]: f for f in self.falas_.get(sessao_id, [])}
        pontos = [{**p, "ordem": ordem[p["fala_id"]]["ordem"], "locutor": ordem[p["fala_id"]]["locutor"]}
                  for p in self.pontos_.get(sessao_id, [])]
        return sorted(pontos, key=lambda p: (p["severidade"] != "alta", p["ordem"]))

    def locutores(self, sessao_id):
        return {k: dict(v) for k, v in self.locutores_.get(sessao_id, {}).items()}

    def definir_papel_manual(self, sessao_id, locutor, papel):
        self.locutores_.setdefault(sessao_id, {})[locutor] = {"papel": papel, "origem": "manual", "confianca": None}

    def definir_papel_automatico(self, sessao_id, locutor, papel, confianca):
        atual = self.locutores_.setdefault(sessao_id, {}).get(locutor)
        if atual is None or atual["origem"] == "auto":
            self.locutores_[sessao_id][locutor] = {"papel": papel, "origem": "auto", "confianca": confianca}


class Estagio2Falso:
    nome = "falso"

    def __init__(self, respostas=None, disponivel=True):
        self.respostas = list(respostas or [])
        self._disponivel = disponivel
        self.chamadas = []
        self.vistas = []              # imagens de cada chamada, para conferir o carimbo da marca
        self.falhar_na_chamada = None  # número da chamada (1, 2…) que deve estourar erro

    def disponivel(self):
        return self._disponivel

    def avaliar(self, imagens):
        if self.falhar_na_chamada == len(self.chamadas) + 1:
            self.chamadas.append(0)
            raise RuntimeError("modelo travou")
        self.chamadas.append(len(imagens))
        self.vistas.append(list(imagens))
        return [self.respostas.pop(0) for _ in imagens]


class FilaGuardada:
    """Fila de trabalho que só anda quando o teste manda, para conferir a ordem e o carimbo."""

    def __init__(self):
        self.tarefas = []

    def enfileirar(self, tarefa, descricao=""):
        self.tarefas.append(tarefa)

    def pendentes(self):
        return len(self.tarefas)

    def executar_todas(self):
        while self.tarefas:
            self.tarefas.pop(0)()


class AnalisadorFalso:
    def __init__(self, resposta=None, erro=None, configurado=True):
        self.resposta, self.erro, self._configurado = resposta, erro, configurado

    def configurado(self):
        return self._configurado

    def analisar(self, texto):
        if self.erro:
            raise self.erro
        return self.resposta or {"sentiment": "neutral", "key_phrases": []}


@dataclass
class Atendimento:
    """Monta os serviços com construtor, como o injector faz, mas com tudo em memória."""

    estagio2: Estagio2Falso = field(default_factory=lambda: Estagio2Falso(disponivel=False))
    analisador: AnalisadorFalso = field(default_factory=lambda: AnalisadorFalso(configurado=False))

    def __post_init__(self):
        self.relogio, self.ids, self.uow = RelogioFixo(), IdsSequenciais(), UnidadeDeTrabalhoFalsa()
        self.pacientes, self.sessoes, self.alertas = PorId(), Sessoes(), Alertas()
        self.leituras, self.eventos, self.confirmacoes, self.autorrelatos = Leituras(), Eventos(), Confirmacoes(), PorSessao()
        self.conversa_repo = Conversa()
        self.duvidas_repo, self.armazem = Duvidas(), ArmazemFalso()
        comum = (self.uow, self.relogio, self.ids)
        self.cadastro = ServicoCadastro(self.pacientes, self.uow)
        self.consulta = ServicoConsulta(self.pacientes, self.sessoes, self.alertas, *comum)
        self.camera = ServicoCamera(self.sessoes, self.leituras, self.eventos, self.confirmacoes, self.alertas,
                                    self.estagio2, *comum)
        self.cascata = ServicoCascataDor(self.sessoes, self.leituras, self.confirmacoes, self.autorrelatos,
                                         self.alertas, self.camera, self.estagio2, *comum)
        self.conversa = ServicoConversa(self.sessoes, self.conversa_repo, self.alertas, self.camera, self.analisador,
                                        *comum)
        self.duvidas = ServicoDuvidas(self.sessoes, self.pacientes, self.leituras, self.confirmacoes, self.duvidas_repo,
                                      self.armazem, *comum)
        self.fila = FilaGuardada()
        self.validacao = ServicoValidacaoDeMarcas(self.duvidas, self.cascata, self.fila)

    def sessao_em_andamento(self) -> str:
        self.cadastro.cadastrar("pac-1", "Ana Lima")
        self.consulta.iniciar("ses-1", "pac-1")
        return "ses-1"
