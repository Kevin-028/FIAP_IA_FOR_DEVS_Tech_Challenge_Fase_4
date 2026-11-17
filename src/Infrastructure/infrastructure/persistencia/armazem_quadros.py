"""Recortes das dúvidas em disco local (porta ArmazemDeQuadros). Nunca saem desta máquina."""
from __future__ import annotations

import os
import re
import shutil

from infrastructure.caminhos import HOSPITAL_DATA

PASTA_PADRAO = os.path.join(HOSPITAL_DATA, "duvidas")
ID_SEGURO = re.compile(r"^[A-Za-z0-9-]{1,64}$")


class ArmazemDeQuadrosEmDisco:
    def __init__(self, pasta: str | None = None) -> None:
        self._pasta = pasta

    def _dir(self, duvida_id: str) -> str:
        if not ID_SEGURO.match(duvida_id):  # o id vira nome de pasta: nada de ../
            raise ValueError("id de dúvida inválido")
        return os.path.join(self._pasta or PASTA_PADRAO, duvida_id)

    def guardar(self, duvida_id: str, quadros: list[bytes]) -> None:
        pasta = self._dir(duvida_id)
        temporaria = pasta + ".parcial"
        os.makedirs(temporaria, exist_ok=True)
        for indice, dados in enumerate(quadros):
            with open(os.path.join(temporaria, f"{indice:02d}.jpg"), "wb") as arquivo:
                arquivo.write(dados)
        if os.path.isdir(pasta):
            shutil.rmtree(pasta)
        os.replace(temporaria, pasta)

    def ler(self, duvida_id: str, indice: int) -> bytes | None:
        caminho = os.path.join(self._dir(duvida_id), f"{int(indice):02d}.jpg")
        if not os.path.isfile(caminho):
            return None
        with open(caminho, "rb") as arquivo:
            return arquivo.read()
