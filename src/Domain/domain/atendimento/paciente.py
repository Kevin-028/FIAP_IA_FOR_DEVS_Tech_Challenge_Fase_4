"""Agregado Paciente: protege o nome e a permanência (RN-05, RN-24)."""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, replace


class NomeInvalido(ValueError):
    """RN-05: sem nome, o cadastro é recusado."""


class PacienteInexistente(LookupError):
    pass


class ExclusaoDePacienteRecusada(Exception):
    """RN-24: o paciente e o histórico permanecem."""


def nome_valido(nome: str) -> str:
    limpo = (nome or "").strip()
    if not limpo:
        raise NomeInvalido("o paciente precisa de um nome")
    return limpo


def chave_de_busca(texto: str) -> str:
    """Sem acento e sem caixa: "Lúcia" e "lucia" se encontram."""
    decomposto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in decomposto if not unicodedata.combining(c)).casefold().strip()


@dataclass(frozen=True)
class Paciente:
    id: str
    nome: str

    @classmethod
    def cadastrar(cls, paciente_id: str, nome: str) -> "Paciente":
        return cls(paciente_id, nome_valido(nome))

    def renomear(self, nome: str) -> "Paciente":
        """Corrigir o nome não troca a identidade: as sessões continuam no mesmo paciente."""
        return replace(self, nome=nome_valido(nome))

    def excluir(self) -> None:
        raise ExclusaoDePacienteRecusada(self.id)
