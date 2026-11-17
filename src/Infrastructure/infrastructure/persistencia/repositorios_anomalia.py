"""Repositórios SQLite do contexto Anomalia de padrão (tabelas artefatos_modelo e alertas_anomalia)."""
from __future__ import annotations

import pickle

from domain.anomalia.alerta import AlertaDeAnomalia
from domain.anomalia.modelo import ModeloDeAnomalia
from infrastructure.persistencia.conexao import ProvedorDeConexao


class RepositorioModeloSqlite:
    def __init__(self, conexao: ProvedorDeConexao) -> None:
        self._conexao = conexao

    def adicionar(self, modelo: ModeloDeAnomalia) -> None:
        self._conexao.atual().execute(
            """
            INSERT INTO artefatos_modelo (id, treinado_no_corpus, formato, conteudo, criado_em)
            VALUES (?, ?, 'isolation-forest', ?, ?)
            """,
            (modelo.id, int(modelo.treinado_no_corpus), pickle.dumps(modelo.artefato), modelo.criado_em),
        )

    def obter(self, modelo_id: str) -> ModeloDeAnomalia | None:
        row = self._conexao.atual().execute(
            "SELECT id, treinado_no_corpus, conteudo, criado_em FROM artefatos_modelo WHERE id = ?",
            (modelo_id,),
        ).fetchone()
        if row is None:
            return None
        # o artefato é gravado pela própria aplicação (treino local), nunca recebido de fora
        artefato = pickle.loads(row["conteudo"]) if row["treinado_no_corpus"] == 1 else None
        return ModeloDeAnomalia(row["id"], row["treinado_no_corpus"] == 1, artefato, row["criado_em"])

    def listar(self) -> list[dict]:
        rows = self._conexao.atual().execute(
            "SELECT id, criado_em FROM artefatos_modelo ORDER BY criado_em DESC"
        ).fetchall()
        return [dict(row) for row in rows]


class RepositorioAlertaAnomaliaSqlite:
    def __init__(self, conexao: ProvedorDeConexao) -> None:
        self._conexao = conexao

    def adicionar(self, alerta: AlertaDeAnomalia) -> None:
        conn = self._conexao.atual()
        conn.execute(
            "INSERT INTO alertas_anomalia (id, serie_id, modelo_id, estado, criado_em) VALUES (?, ?, ?, ?, ?)",
            (alerta.id, alerta.serie_id, alerta.modelo_id, alerta.estado, alerta.criado_em),
        )
        conn.executemany(
            "INSERT INTO alertas_anomalia_sinais (alerta_id, sinal) VALUES (?, ?)",
            [(alerta.id, sinal) for sinal in alerta.sinais],
        )

    def listar(self) -> list[dict]:
        rows = self._conexao.atual().execute(
            """
            SELECT a.id, a.serie_id, a.modelo_id, a.estado, a.criado_em, group_concat(s.sinal, ', ') AS sinais
              FROM alertas_anomalia a LEFT JOIN alertas_anomalia_sinais s ON s.alerta_id = a.id
             GROUP BY a.id ORDER BY a.criado_em DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
