"""Fila em segundo plano: um trabalho por vez, na ordem, sem travar em erro e sem prender conexão do banco."""
from __future__ import annotations

import threading
import time

from infrastructure.fila import FilaEmSegundoPlano


class ConexaoFalsa:
    def __init__(self):
        self.fechadas = []

    def fechar(self):
        self.fechadas.append(threading.current_thread().name)


def test_executa_em_ordem_um_de_cada_vez_fora_da_requisicao():
    conexao = ConexaoFalsa()
    fila = FilaEmSegundoPlano(conexao)
    feitos, ao_mesmo_tempo, rodando = [], [], [0]

    def tarefa(n):
        def executar():
            rodando[0] += 1
            ao_mesmo_tempo.append(rodando[0])
            time.sleep(0.02)
            feitos.append((n, threading.current_thread().name))
            rodando[0] -= 1
        return executar

    for n in range(5):
        fila.enfileirar(tarefa(n), f"t{n}")
    assert fila.aguardar(timeout=5)
    assert [n for n, _ in feitos] == [0, 1, 2, 3, 4]
    assert max(ao_mesmo_tempo) == 1                       # nunca dois validadores juntos
    assert {t for _, t in feitos} == {"fila-validador"}   # nada roda na thread da requisição
    assert fila.pendentes() == 0 and len(conexao.fechadas) == 5


def test_erro_numa_tarefa_nao_derruba_a_fila():
    fila = FilaEmSegundoPlano(ConexaoFalsa())
    feitos = []

    def quebra():
        raise RuntimeError("modelo travou")

    fila.enfileirar(quebra, "quebra")
    fila.enfileirar(lambda: feitos.append("depois"), "depois")
    assert fila.aguardar(timeout=5)
    assert feitos == ["depois"]


def test_pendentes_conta_quem_espera_e_quem_esta_rodando():
    fila = FilaEmSegundoPlano(ConexaoFalsa())
    liberar = threading.Event()
    fila.enfileirar(liberar.wait, "segura")
    fila.enfileirar(lambda: None, "espera")
    time.sleep(0.05)
    assert fila.pendentes() == 2
    liberar.set()
    assert fila.aguardar(timeout=5) and fila.pendentes() == 0
