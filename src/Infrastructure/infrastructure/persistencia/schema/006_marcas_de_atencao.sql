-- Marcas de atenção da dor (ADR-004): toda suspeita do estágio 1 é gravada na hora.
-- O veredito do estágio 2 chega depois (avaliando -> confirmada | descartada | sem_resultado) e só auxilia.
-- Os recortes (2 a 4 s) continuam em hospital_data/duvidas/<id>/.

CREATE TABLE duvidas_dor_nova (
    id TEXT PRIMARY KEY,
    sessao_id TEXT NOT NULL REFERENCES sessoes(id) ON DELETE RESTRICT,
    criado_em TEXT NOT NULL,
    duracao_s REAL NOT NULL CHECK (duracao_s BETWEEN 2 AND 4),
    quadros INTEGER NOT NULL,
    wong_baker_estimado INTEGER,
    dor_relativa REAL,
    veredito TEXT NOT NULL DEFAULT 'avaliando'
        CHECK (veredito IN ('avaliando', 'confirmada', 'descartada', 'sem_resultado')),
    confirmacao_id TEXT UNIQUE REFERENCES confirmacoes_dor(id) ON DELETE RESTRICT,
    veredito_face INTEGER,
    veredito_dor_relativa REAL,
    veredito_em TEXT,
    face_classificada INTEGER CHECK (face_classificada IS NULL OR face_classificada IN (0, 2, 4, 6, 8, 10)),
    categoria TEXT CHECK (categoria IS NULL OR categoria IN ('dor', 'sem_dor', 'outra_expressao', 'imagem_ruim')),
    observacao TEXT,
    classificada_em TEXT
);

-- dúvidas antigas já nasceram com o veredito do validador
INSERT INTO duvidas_dor_nova (id, sessao_id, criado_em, duracao_s, quadros, wong_baker_estimado, dor_relativa,
                              veredito, confirmacao_id, veredito_face, veredito_dor_relativa, veredito_em,
                              face_classificada, categoria, observacao, classificada_em)
SELECT d.id, d.sessao_id, d.criado_em, d.duracao_s, d.quadros, d.wong_baker_estimado, d.dor_relativa,
       CASE WHEN c.confirmado = 1 THEN 'confirmada' ELSE 'descartada' END, d.confirmacao_id, c.wong_baker,
       c.dor_relativa, c.registrado_em, d.face_classificada, d.categoria, d.observacao, d.classificada_em
  FROM duvidas_dor d JOIN confirmacoes_dor c ON c.id = d.confirmacao_id;

DROP INDEX IF EXISTS ix_duvidas_dor_pendentes;
DROP TABLE duvidas_dor;
ALTER TABLE duvidas_dor_nova RENAME TO duvidas_dor;
CREATE INDEX IF NOT EXISTS ix_duvidas_dor_pendentes ON duvidas_dor(classificada_em, criado_em);
