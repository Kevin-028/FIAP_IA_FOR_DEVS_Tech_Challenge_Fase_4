"""Alerta da fila do plantão: aberto → reconhecido → fechado. Nunca prescreve."""
from __future__ import annotations

from dataclasses import dataclass, replace

ABERTO, RECONHECIDO, FECHADO = "open", "acked", "closed"
STATUS = (ABERTO, RECONHECIDO, FECHADO)


@dataclass(frozen=True)
class AlertaDoPlantao:
    id: int
    patient_id: str
    thread_id: str
    severity: str
    reason: str
    source: str
    status: str
    created_at: str
    acked_at: str | None = None
    closed_at: str | None = None

    def reconhecer(self, quando: str) -> "AlertaDoPlantao":
        """Reconhecer um alerta já reconhecido ou fechado não muda nada."""
        if self.status != ABERTO:
            return self
        return replace(self, status=RECONHECIDO, acked_at=quando)

    def fechar(self, quando: str) -> "AlertaDoPlantao":
        return replace(self, status=FECHADO, acked_at=self.acked_at or quando, closed_at=quando)


def fio_do_paciente(patient_id: str) -> str:
    return f"fase4-{patient_id}"


def achados_para_alerta(resultado_da_fusao: dict) -> list[dict]:
    """Só a fusão de nível alto vira alerta na fila."""
    if resultado_da_fusao.get("level") != "high":
        return []
    return list(resultado_da_fusao["findings"])
