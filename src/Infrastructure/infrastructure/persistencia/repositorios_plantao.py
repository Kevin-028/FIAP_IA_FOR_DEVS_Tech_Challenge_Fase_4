"""Repositórios SQLite do contexto Plantão, sobre as tabelas do banco.py (patients, vitals, alerts...)."""
from __future__ import annotations

from domain.plantao.alerta import AlertaDoPlantao
from infrastructure.persistencia import banco
from infrastructure.persistencia.conexao import ProvedorDeConexao
from infrastructure.persistencia.seed import store_patient


class RepositorioPlantaoSqlite:
    def __init__(self, conexao: ProvedorDeConexao) -> None:
        self._conexao = conexao

    @property
    def _conn(self):
        return self._conexao.atual()

    def paciente(self, patient_id: str) -> dict | None:
        return banco.get_patient(self._conn, patient_id)

    def pacientes_challenge(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM patients WHERE notes LIKE 'PhysioNet Challenge 2019%' ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]

    def gravar_registro(self, item: dict) -> None:
        store_patient(self._conn, item)

    def vitais(self, patient_id: str) -> list[dict]:
        return banco.list_vitals(self._conn, patient_id)

    def prescricoes(self, patient_id: str) -> list[dict]:
        return banco.list_prescriptions(self._conn, patient_id)

    def movimentos(self, patient_id: str) -> list[dict]:
        return banco.list_movement(self._conn, patient_id)

    def adicionar_vital(self, patient_id: str, vital: dict) -> None:
        banco.insert_vital(self._conn, patient_id, vital["recorded_at"], vital["hr"], vital["sbp"], vital["dbp"],
                           vital["spo2"])

    def adicionar_movimento(self, patient_id: str, movimento: dict) -> None:
        banco.insert_movement(self._conn, patient_id, movimento["recorded_at"], movimento["posture"], movimento["zone"])

    def limpar_monitor(self, patient_id: str, thread_id: str) -> None:
        self._conn.execute("DELETE FROM vitals WHERE patient_id = ?", (patient_id,))
        self._conn.execute("DELETE FROM movement_events WHERE patient_id = ?", (patient_id,))
        self._conn.execute("DELETE FROM alerts WHERE thread_id = ?", (thread_id,))

    def salvar_relatorio(self, patient_id: str, tipo: str, corpo: dict) -> None:
        banco.save_modality_report(self._conn, patient_id, tipo, corpo)

    def tipos_de_relatorio(self, patient_id: str) -> set[str]:
        return banco.modality_report_kinds(self._conn, patient_id)


class RepositorioAlertaPlantaoSqlite:
    def __init__(self, conexao: ProvedorDeConexao) -> None:
        self._conexao = conexao

    def emitir(self, patient_id: str, thread_id: str, achado: dict) -> bool:
        return banco.emit_alert(self._conexao.atual(), patient_id=patient_id, thread_id=thread_id,
                                severity=achado["severity"], reason=achado["reason"], source=achado["source"])

    def obter(self, alerta_id: int) -> AlertaDoPlantao | None:
        row = banco.get_alert(self._conexao.atual(), alerta_id)
        return AlertaDoPlantao(**row) if row else None

    def salvar(self, alerta: AlertaDoPlantao) -> None:
        self._conexao.atual().execute(
            "UPDATE alerts SET status = ?, acked_at = ?, closed_at = ? WHERE id = ?",
            (alerta.status, alerta.acked_at, alerta.closed_at, alerta.id),
        )

    def listar(self, status: str | None = None) -> list[dict]:
        return banco.list_alerts(self._conexao.atual(), status)

    def abertos(self) -> int:
        return banco.open_alert_count(self._conexao.atual())
