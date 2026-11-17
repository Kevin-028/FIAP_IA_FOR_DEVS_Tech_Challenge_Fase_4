"""ACL do corpus PhysioNet Challenge 2019 para o treino (porta CorpusVital).

Lê os .psv e entrega só hr, sbp, dbp e spo2. O SepsisLabel não atravessa e a série não vira paciente.
"""
from __future__ import annotations

import os

from infrastructure.physionet.challenge2019 import find_path, read_record

LINHAS_POR_MODELO = 400 * 20
CAMPOS = ("hr", "sbp", "dbp", "spo2")


def pastas_corpus(raiz: str) -> list[str]:
    base = os.path.join(raiz, "hospital_data", "fase4", "challenge-2019", "training")
    irma = os.path.normpath(os.path.join(raiz, "..", "Fase_3", "hospital_data", "fase4", "challenge-2019", "training"))
    return [os.path.join(pasta, s) for pasta in (base, irma) for s in ("training_setA", "training_setB")]


class CorpusChallenge2019:
    def __init__(self, raiz: str) -> None:
        self._raiz = raiz

    def linhas_de_treino(self) -> list[dict]:
        linhas: list[dict] = []
        for pasta in pastas_corpus(self._raiz):
            if not os.path.isdir(pasta):
                continue
            for nome in sorted(os.listdir(pasta)):
                if not nome.endswith(".psv"):
                    continue
                linhas.extend({c: row[c] for c in CAMPOS} for row in read_record(os.path.join(pasta, nome)))
                if len(linhas) >= LINHAS_POR_MODELO:
                    return linhas
        return linhas

    def serie(self, serie_id: str) -> list[dict] | None:
        encontrado = find_path(serie_id)
        if encontrado is None:
            return None
        return [{c: row[c] for c in CAMPOS} for row in read_record(encontrado[2])]
