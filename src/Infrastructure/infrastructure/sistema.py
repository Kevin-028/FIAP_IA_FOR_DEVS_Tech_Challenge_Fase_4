"""Relógio e gerador de ids reais (portas Relogio e GeradorDeId)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone


class RelogioUtc:
    def agora(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class GeradorUuid:
    def novo(self) -> str:
        return str(uuid.uuid4())
