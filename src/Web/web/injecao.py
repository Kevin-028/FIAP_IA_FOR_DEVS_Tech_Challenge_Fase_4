"""Controllers pedem o serviço pelo tipo; quem monta é o injector registrado no app."""
from __future__ import annotations

from typing import TypeVar

from flask import current_app

T = TypeVar("T")


def servico(tipo: type[T]) -> T:
    return current_app.extensions["injector"].get(tipo)
