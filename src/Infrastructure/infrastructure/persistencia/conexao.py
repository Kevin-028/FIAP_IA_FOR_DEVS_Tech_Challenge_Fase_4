"""Uma conexão SQLite por requisição (ou por thread), compartilhada pelos repositórios e pela unidade de trabalho."""
from __future__ import annotations

import sqlite3
import threading

from infrastructure.persistencia.banco import connect, init_db


class ProvedorDeConexao:
    """Abre na primeira consulta e aplica o schema; a Web fecha ao fim da requisição."""

    def __init__(self, caminho: str | None = None) -> None:
        self.caminho = caminho
        self._local = threading.local()

    def atual(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = connect(self.caminho)
            init_db(conn)
            self._local.conn = conn
        return conn

    def fechar(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None


class UnidadeDeTrabalhoSqlite:
    def __init__(self, conexao: ProvedorDeConexao) -> None:
        self._conexao = conexao

    def commit(self) -> None:
        self._conexao.atual().commit()
