"""Repositórios SQLite do contexto Atendimento. Todo o SQL do consultório fica aqui."""
from __future__ import annotations

import json
from dataclasses import fields

from domain.atendimento.alerta_dor import AlertaDeDor
from domain.atendimento.duvida import DuvidaDeDor
from domain.atendimento.paciente import Paciente
from domain.atendimento.sessao import LeituraDaSessao, Sessao
from infrastructure.persistencia.conexao import ProvedorDeConexao

_CAMPOS_LEITURA = ("texto_fala", "termos_criticos", "sentimento", "alteracao_vocal", "postura", "face", "objetos_areas")


class _Repositorio:
    def __init__(self, conexao: ProvedorDeConexao) -> None:
        self._conexao = conexao

    def _sql(self, sql: str, params=()):
        return self._conexao.atual().execute(sql, params)


class RepositorioPacienteSqlite(_Repositorio):
    def adicionar(self, paciente: Paciente) -> None:
        self._sql("INSERT INTO pacientes (id, nome) VALUES (?, ?)", (paciente.id, paciente.nome))

    def obter(self, paciente_id: str) -> Paciente | None:
        row = self._sql("SELECT id, nome FROM pacientes WHERE id = ?", (paciente_id,)).fetchone()
        return Paciente(row["id"], row["nome"]) if row else None

    def salvar(self, paciente: Paciente) -> None:
        self._sql("UPDATE pacientes SET nome = ? WHERE id = ?", (paciente.nome, paciente.id))

    def listar(self) -> list[Paciente]:
        return [Paciente(r["id"], r["nome"]) for r in self._sql("SELECT id, nome FROM pacientes ORDER BY nome, id")]


class RepositorioSessaoSqlite(_Repositorio):
    def adicionar(self, sessao: Sessao) -> None:
        self._sql(
            "INSERT INTO sessoes (id, paciente_id, estado, iniciada_em) VALUES (?, ?, ?, ?)",
            (sessao.id, sessao.paciente_id, sessao.estado, sessao.iniciada_em),
        )

    def obter(self, sessao_id: str) -> Sessao | None:
        row = self._sql("SELECT * FROM sessoes WHERE id = ?", (sessao_id,)).fetchone()
        if row is None:
            return None
        leitura = LeituraDaSessao(**{c: row[c] for c in _CAMPOS_LEITURA})
        return Sessao(row["id"], row["paciente_id"], row["estado"], leitura, row["iniciada_em"], row["encerrada_em"])

    def _sessoes(self, where: str, params=(), ordem: str = "iniciada_em") -> list[Sessao]:
        ids = [r["id"] for r in self._sql(f"SELECT id FROM sessoes WHERE {where} ORDER BY {ordem}", params)]
        return [self.obter(i) for i in ids]

    def do_paciente(self, paciente_id: str) -> list[Sessao]:
        return self._sessoes("paciente_id = ?", (paciente_id,), "iniciada_em DESC, rowid DESC")

    def em_andamento(self) -> list[Sessao]:
        return self._sessoes("estado = 'em_andamento'")

    def salvar(self, sessao: Sessao) -> None:
        campos = {c: getattr(sessao.leitura, c) for c in _CAMPOS_LEITURA}
        atribuicoes = ", ".join(f"{c} = :{c}" for c in campos)
        self._sql(
            f"UPDATE sessoes SET estado = :estado, encerrada_em = :encerrada_em, {atribuicoes} WHERE id = :id",
            {**campos, "estado": sessao.estado, "encerrada_em": sessao.encerrada_em, "id": sessao.id},
        )


class RepositorioAlertaDorSqlite(_Repositorio):
    _COLUNAS = "id, sessao_id, origem, descricao_sinal, estado, criado_em, ciente_em, encerrado_em"

    def adicionar(self, alerta: AlertaDeDor) -> None:
        self._sql(
            f"INSERT INTO alertas_dor ({self._COLUNAS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (alerta.id, alerta.sessao_id, alerta.origem, alerta.descricao_sinal, alerta.estado, alerta.criado_em,
             alerta.ciente_em, alerta.encerrado_em),
        )

    def obter(self, alerta_id: str) -> AlertaDeDor | None:
        row = self._sql(f"SELECT {self._COLUNAS} FROM alertas_dor WHERE id = ?", (alerta_id,)).fetchone()
        return AlertaDeDor(**dict(row)) if row else None

    def salvar(self, alerta: AlertaDeDor) -> None:
        self._sql(
            "UPDATE alertas_dor SET estado = ?, ciente_em = ?, encerrado_em = ? WHERE id = ?",
            (alerta.estado, alerta.ciente_em, alerta.encerrado_em, alerta.id),
        )

    def da_sessao(self, sessao_id: str) -> list[AlertaDeDor]:
        rows = self._sql(
            f"SELECT {self._COLUNAS} FROM alertas_dor WHERE sessao_id = ? ORDER BY criado_em, id", (sessao_id,)
        )
        return [AlertaDeDor(**dict(row)) for row in rows]

    def ativos(self) -> list[AlertaDeDor]:
        rows = self._sql(f"SELECT {self._COLUNAS} FROM alertas_dor WHERE estado != 'encerrado' ORDER BY criado_em, id")
        return [AlertaDeDor(**dict(row)) for row in rows]


class RepositorioLeituraFaceSqlite(_Repositorio):
    def adicionar(self, sessao_id: str, leitura: dict) -> None:
        self._sql(
            """
            INSERT INTO leituras_face
                (id, sessao_id, registrado_em, expressao, valencia, dor_pspi, dor_relativa, nivel_dor, wong_baker, scores)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (leitura["id"], sessao_id, leitura["registrado_em"], leitura["expressao"], leitura["valencia"],
             leitura["dor_pspi"], leitura["dor_relativa"], leitura["nivel_dor"], leitura["wong_baker"],
             json.dumps(leitura["scores"])),
        )

    def pspi_iniciais(self, sessao_id: str, limite: int) -> list[float]:
        rows = self._sql(
            "SELECT dor_pspi FROM leituras_face WHERE sessao_id = ? ORDER BY registrado_em, rowid LIMIT ?",
            (sessao_id, limite),
        )
        return [row["dor_pspi"] for row in rows]

    def recentes(self, sessao_id: str, limite: int) -> list[dict]:
        rows = self._sql(
            "SELECT expressao, nivel_dor, wong_baker FROM leituras_face WHERE sessao_id = ? "
            "ORDER BY registrado_em DESC, rowid DESC LIMIT ?",
            (sessao_id, limite),
        )
        return [dict(row) for row in rows]

    def ultima(self, sessao_id: str) -> dict | None:
        row = self._sql(
            """
            SELECT registrado_em, expressao, valencia, dor_pspi, dor_relativa, nivel_dor, wong_baker, scores
              FROM leituras_face WHERE sessao_id = ? ORDER BY registrado_em DESC, rowid DESC LIMIT 1
            """,
            (sessao_id,),
        ).fetchone()
        if row is None:
            return None
        return {**dict(row), "scores": json.loads(row["scores"])}


class RepositorioEventoFaceSqlite(_Repositorio):
    def adicionar(self, sessao_id: str, evento: dict) -> None:
        self._sql(
            """
            INSERT INTO eventos_face (id, sessao_id, registrado_em, tipo, expressao, descricao)
            VALUES (:id, :sessao_id, :registrado_em, :tipo, :expressao, :descricao)
            """,
            {**evento, "sessao_id": sessao_id},
        )

    def ultima_expressao(self, sessao_id: str) -> str | None:
        row = self._sql(
            "SELECT expressao FROM eventos_face WHERE sessao_id = ? AND tipo = 'expressao' "
            "ORDER BY registrado_em DESC, rowid DESC LIMIT 1",
            (sessao_id,),
        ).fetchone()
        return row["expressao"] if row else None

    def da_sessao(self, sessao_id: str) -> list[dict]:
        rows = self._sql(
            "SELECT id, registrado_em, tipo, expressao, descricao FROM eventos_face "
            "WHERE sessao_id = ? ORDER BY registrado_em, rowid",
            (sessao_id,),
        )
        return [dict(row) for row in rows]


class RepositorioConfirmacaoDorSqlite(_Repositorio):
    def adicionar(self, sessao_id: str, confirmacao: dict) -> None:
        self._sql(
            """
            INSERT INTO confirmacoes_dor (id, sessao_id, registrado_em, detector, pspi, pspi_base, dor_relativa,
                                          wong_baker, confirmado, faces_avaliadas)
            VALUES (:id, :sessao_id, :registrado_em, :detector, :pspi, :pspi_base, :dor_relativa,
                    :wong_baker, :confirmado, :faces_avaliadas)
            """,
            {**confirmacao, "sessao_id": sessao_id, "confirmado": int(confirmacao["confirmado"])},
        )

    def ultima(self, sessao_id: str) -> dict | None:
        row = self._sql(
            "SELECT * FROM confirmacoes_dor WHERE sessao_id = ? ORDER BY registrado_em DESC, rowid DESC LIMIT 1",
            (sessao_id,),
        ).fetchone()
        return {**dict(row), "confirmado": bool(row["confirmado"])} if row else None

    def obter(self, confirmacao_id: str) -> dict | None:
        row = self._sql("SELECT * FROM confirmacoes_dor WHERE id = ?", (confirmacao_id,)).fetchone()
        return {**dict(row), "confirmado": bool(row["confirmado"])} if row else None


class RepositorioDuvidaSqlite(_Repositorio):
    _COLUNAS = tuple(campo.name for campo in fields(DuvidaDeDor))
    _MUTAVEIS = ("veredito", "confirmacao_id", "veredito_face", "veredito_dor_relativa", "veredito_em",
                 "face_classificada", "categoria", "observacao", "classificada_em")

    def adicionar(self, duvida: DuvidaDeDor) -> None:
        colunas = ", ".join(self._COLUNAS)
        valores = ", ".join(":" + c for c in self._COLUNAS)
        self._sql(f"INSERT INTO duvidas_dor ({colunas}) VALUES ({valores})", duvida.__dict__)

    def obter(self, duvida_id: str) -> DuvidaDeDor | None:
        row = self._sql("SELECT * FROM duvidas_dor WHERE id = ?", (duvida_id,)).fetchone()
        return DuvidaDeDor(**{c: row[c] for c in self._COLUNAS}) if row else None

    def salvar(self, duvida: DuvidaDeDor) -> None:
        """Veredito do validador e classificação do médico; o recorte não muda."""
        atribuicoes = ", ".join(f"{c} = :{c}" for c in self._MUTAVEIS)
        self._sql(f"UPDATE duvidas_dor SET {atribuicoes} WHERE id = :id", duvida.__dict__)

    def listar(self, pendentes: bool | None = None) -> list[DuvidaDeDor]:
        filtro = {True: "WHERE classificada_em IS NULL", False: "WHERE classificada_em IS NOT NULL", None: ""}[pendentes]
        rows = self._sql(f"SELECT * FROM duvidas_dor {filtro} ORDER BY criado_em DESC, rowid DESC")
        return [DuvidaDeDor(**{c: row[c] for c in self._COLUNAS}) for row in rows]


class RepositorioAutorrelatoSqlite(_Repositorio):
    def adicionar(self, sessao_id: str, relato: dict) -> None:
        self._sql(
            "INSERT INTO autorrelatos_dor (id, sessao_id, registrado_em, wong_baker, estimado, origem_estimativa) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (relato["id"], sessao_id, relato["registrado_em"], relato["wong_baker"], relato["estimado"],
             relato["origem_estimativa"]),
        )


class RepositorioConversaSqlite(_Repositorio):
    def proxima_ordem(self, sessao_id: str) -> int:
        return self._sql("SELECT COALESCE(MAX(ordem), 0) + 1 FROM falas WHERE sessao_id = ?", (sessao_id,)).fetchone()[0]

    def adicionar_fala(self, sessao_id: str, fala: dict) -> None:
        self._sql(
            """
            INSERT INTO falas (id, sessao_id, ordem, locutor, texto, offset_ms, sentimento, frases_chave,
                               expressao_face, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (fala["id"], sessao_id, fala["ordem"], fala["locutor"], fala["texto"], fala["offset_ms"],
             fala["sentimento"], ", ".join(fala["frases_chave"]), fala["expressao_face"], fala["criado_em"]),
        )

    def adicionar_ponto(self, sessao_id: str, ponto: dict) -> None:
        self._sql(
            """
            INSERT INTO pontos_atencao (id, sessao_id, fala_id, categoria, trecho, motivo, severidade, origem, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ponto["id"], sessao_id, ponto["fala_id"], ponto["categoria"], ponto["trecho"], ponto["motivo"],
             ponto["severidade"], ponto["origem"], ponto["criado_em"]),
        )

    def falas(self, sessao_id: str) -> list[dict]:
        rows = self._sql(
            """
            SELECT id, ordem, locutor, texto, offset_ms, sentimento, frases_chave, expressao_face, criado_em
              FROM falas WHERE sessao_id = ? ORDER BY ordem
            """,
            (sessao_id,),
        )
        return [{**dict(r), "frases_chave": [f for f in (r["frases_chave"] or "").split(", ") if f]} for r in rows]

    def pontos(self, sessao_id: str) -> list[dict]:
        rows = self._sql(
            """
            SELECT p.id, p.fala_id, f.ordem, f.locutor, p.categoria, p.trecho, p.motivo, p.severidade, p.origem
              FROM pontos_atencao p JOIN falas f ON f.id = p.fala_id
             WHERE p.sessao_id = ?
             ORDER BY CASE p.severidade WHEN 'alta' THEN 0 ELSE 1 END, f.ordem
            """,
            (sessao_id,),
        )
        return [dict(row) for row in rows]

    def locutores(self, sessao_id: str) -> dict[str, dict]:
        rows = self._sql(
            "SELECT locutor, papel, origem, confianca FROM sessao_locutores WHERE sessao_id = ?", (sessao_id,)
        )
        return {r["locutor"]: {"papel": r["papel"], "origem": r["origem"], "confianca": r["confianca"]} for r in rows}

    def definir_papel_manual(self, sessao_id: str, locutor: str, papel: str) -> None:
        self._sql(
            """
            INSERT INTO sessao_locutores (sessao_id, locutor, papel, origem, confianca) VALUES (?, ?, ?, 'manual', NULL)
            ON CONFLICT (sessao_id, locutor) DO UPDATE SET papel = excluded.papel, origem = 'manual', confianca = NULL
            """,
            (sessao_id, locutor, papel),
        )

    def definir_papel_automatico(self, sessao_id: str, locutor: str, papel: str, confianca: float) -> None:
        self._sql(
            """
            INSERT INTO sessao_locutores (sessao_id, locutor, papel, origem, confianca) VALUES (?, ?, ?, 'auto', ?)
            ON CONFLICT (sessao_id, locutor) DO UPDATE SET papel = excluded.papel, confianca = excluded.confianca
             WHERE sessao_locutores.origem = 'auto'
            """,
            (sessao_id, locutor, papel, confianca),
        )
