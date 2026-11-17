-- Transcrição ao vivo da consulta e pontos de atenção marcados em cada fala.
-- Aditiva: não altera as tabelas de 001_consultorio.
--
--   Fala da consulta     → falas (uma linha por frase finalizada pelo Azure Speech)
--   Papel do locutor     → sessao_locutores (Guest-1 = médico, Guest-2 = paciente)
--   Ponto de atenção     → pontos_atencao (aponta a fala e o trecho que o gerou)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS falas (
    id TEXT PRIMARY KEY,
    sessao_id TEXT NOT NULL REFERENCES sessoes(id) ON DELETE RESTRICT,
    ordem INTEGER NOT NULL,
    locutor TEXT NOT NULL DEFAULT '',
    texto TEXT NOT NULL CHECK (length(texto) > 0),
    offset_ms INTEGER,
    sentimento TEXT NOT NULL DEFAULT '',
    frases_chave TEXT NOT NULL DEFAULT '',
    criado_em TEXT NOT NULL,
    UNIQUE (sessao_id, ordem)
);

CREATE TABLE IF NOT EXISTS sessao_locutores (
    sessao_id TEXT NOT NULL REFERENCES sessoes(id) ON DELETE RESTRICT,
    locutor TEXT NOT NULL,
    papel TEXT NOT NULL CHECK (papel IN ('medico', 'paciente', 'acompanhante')),
    PRIMARY KEY (sessao_id, locutor)
);

CREATE TABLE IF NOT EXISTS pontos_atencao (
    id TEXT PRIMARY KEY,
    sessao_id TEXT NOT NULL REFERENCES sessoes(id) ON DELETE RESTRICT,
    fala_id TEXT NOT NULL REFERENCES falas(id) ON DELETE RESTRICT,
    categoria TEXT NOT NULL,
    trecho TEXT NOT NULL,
    motivo TEXT NOT NULL,
    severidade TEXT NOT NULL CHECK (severidade IN ('alta', 'media')),
    origem TEXT NOT NULL CHECK (origem IN ('regra', 'azure')),
    criado_em TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_falas_sessao ON falas(sessao_id, ordem);
CREATE INDEX IF NOT EXISTS ix_pontos_atencao_sessao ON pontos_atencao(sessao_id);

CREATE TRIGGER IF NOT EXISTS falas_recusa_delete
BEFORE DELETE ON falas
BEGIN
    SELECT RAISE(ABORT, 'exclusao de fala recusada');
END;

CREATE TRIGGER IF NOT EXISTS pontos_atencao_recusa_delete
BEFORE DELETE ON pontos_atencao
BEGIN
    SELECT RAISE(ABORT, 'exclusao de ponto de atencao recusada');
END;
