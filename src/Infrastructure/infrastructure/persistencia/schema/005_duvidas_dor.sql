-- Dúvidas da cascata de dor (ADR-004): só os momentos de desacordo ou perto do limiar.
-- Os recortes (2 a 4 s) ficam em hospital_data/duvidas/<id>/; aqui ficam o motivo e a classificação do médico.

CREATE TABLE IF NOT EXISTS duvidas_dor (
    id TEXT PRIMARY KEY,
    sessao_id TEXT NOT NULL REFERENCES sessoes(id) ON DELETE RESTRICT,
    confirmacao_id TEXT NOT NULL UNIQUE REFERENCES confirmacoes_dor(id) ON DELETE RESTRICT,
    motivo TEXT NOT NULL CHECK (motivo IN ('suspeita_descartada', 'perto_do_limiar')),
    criado_em TEXT NOT NULL,
    duracao_s REAL NOT NULL CHECK (duracao_s BETWEEN 2 AND 4),
    quadros INTEGER NOT NULL,
    wong_baker_estimado INTEGER NOT NULL,
    dor_relativa REAL NOT NULL,
    face_classificada INTEGER CHECK (face_classificada IS NULL OR face_classificada IN (0, 2, 4, 6, 8, 10)),
    categoria TEXT CHECK (categoria IS NULL OR categoria IN ('dor', 'sem_dor', 'outra_expressao', 'imagem_ruim')),
    observacao TEXT,
    classificada_em TEXT
);

CREATE INDEX IF NOT EXISTS ix_duvidas_dor_pendentes ON duvidas_dor(classificada_em, criado_em);
