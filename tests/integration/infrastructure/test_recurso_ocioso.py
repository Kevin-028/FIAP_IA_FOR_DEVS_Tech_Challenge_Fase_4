"""Modelo pesado mantido em memória entre pedidos e liberado após ociosidade ou no encerramento."""
from __future__ import annotations

import threading

from infrastructure.ia.recurso_ocioso import RecursoComOciosidade


class Relogio:
    def __init__(self):
        self.agora = 0.0

    def __call__(self):
        return self.agora


def _recurso(ociosidade=120.0):
    cargas = []
    relogio = Relogio()

    def carregar():
        cargas.append(len(cargas) + 1)
        return {"modelo": len(cargas)}

    return RecursoComOciosidade(carregar, ociosidade_s=ociosidade, relogio=relogio, agendar=False), cargas, relogio


def test_carrega_so_no_primeiro_pedido_e_reaproveita():
    recurso, cargas, relogio = _recurso()
    assert recurso.carregado is False and cargas == []
    primeiro = recurso.obter()
    relogio.agora = 100
    assert recurso.obter() is primeiro and cargas == [1]


def test_libera_apos_ociosidade_e_recarrega_no_proximo_pedido():
    recurso, cargas, relogio = _recurso()
    recurso.obter()
    relogio.agora = 119
    assert recurso.verificar_ociosidade() is False and recurso.carregado
    relogio.agora = 120
    assert recurso.verificar_ociosidade() is True and recurso.carregado is False
    recurso.obter()
    assert cargas == [1, 2]


def test_cada_pedido_renova_o_prazo():
    recurso, _, relogio = _recurso()
    recurso.obter()
    relogio.agora = 100
    recurso.obter()
    relogio.agora = 200  # 100 s depois do último uso
    assert recurso.verificar_ociosidade() is False and recurso.carregado


def test_liberar_no_encerramento_e_idempotente():
    recurso, _, _ = _recurso()
    recurso.obter()
    recurso.liberar()
    recurso.liberar()
    assert recurso.carregado is False


def test_pedidos_simultaneos_carregam_uma_vez():
    cargas = []
    liberar = threading.Event()

    def carregar():
        cargas.append(1)
        liberar.wait(1)
        return object()

    recurso = RecursoComOciosidade(carregar, ociosidade_s=120, agendar=False)
    threads = [threading.Thread(target=recurso.obter) for _ in range(5)]
    for t in threads:
        t.start()
    liberar.set()
    for t in threads:
        t.join(2)
    assert cargas == [1]


def test_temporizador_real_libera_sozinho():
    recurso = RecursoComOciosidade(lambda: object(), ociosidade_s=0.05)
    recurso.obter()
    for _ in range(40):
        if not recurso.carregado:
            break
        threading.Event().wait(0.05)
    assert recurso.carregado is False
