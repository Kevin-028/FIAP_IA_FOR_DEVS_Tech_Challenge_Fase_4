-- Cascata de dor facial: escala Wong-Baker, confirmação do estágio 2 e autorrelato do paciente.
-- Aditiva: uma coluna nova com valor padrão e duas tabelas novas.
--
--   leituras_face.wong_baker   face estimada pelo estágio 1 (MediaPipe, a cada ~1 s)
--   confirmacoes_dor           resultado do estágio 2 (Py-Feat) quando o estágio 1 suspeitou de dor
--   autorrelatos_dor           face que o próprio paciente apontou, ao lado da estimativa da época
--
-- Nenhuma imagem é gravada: os recortes do rosto do estágio 2 são processados em memória e descartados.

ALTER TABLE leituras_face ADD COLUMN wong_baker INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS confirmacoes_dor (
    id TEXT PRIMARY KEY,
    sessao_id TEXT NOT NULL REFERENCES sessoes(id) ON DELETE RESTRICT,
    registrado_em TEXT NOT NULL,
    detector TEXT NOT NULL,
    pspi REAL NOT NULL,
    pspi_base REAL NOT NULL,
    dor_relativa REAL NOT NULL,
    wong_baker INTEGER NOT NULL CHECK (wong_baker IN (0, 2, 4, 6, 8, 10)),
    confirmado INTEGER NOT NULL CHECK (confirmado IN (0, 1)),
    faces_avaliadas INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS autorrelatos_dor (
    id TEXT PRIMARY KEY,
    sessao_id TEXT NOT NULL REFERENCES sessoes(id) ON DELETE RESTRICT,
    registrado_em TEXT NOT NULL,
    wong_baker INTEGER NOT NULL CHECK (wong_baker IN (0, 2, 4, 6, 8, 10)),
    estimado INTEGER CHECK (estimado IS NULL OR estimado IN (0, 2, 4, 6, 8, 10)),
    origem_estimativa TEXT CHECK (origem_estimativa IS NULL OR origem_estimativa IN ('estagio1', 'estagio2'))
);

CREATE INDEX IF NOT EXISTS ix_confirmacoes_dor_sessao ON confirmacoes_dor(sessao_id, registrado_em);
CREATE INDEX IF NOT EXISTS ix_autorrelatos_dor_sessao ON autorrelatos_dor(sessao_id, registrado_em);
