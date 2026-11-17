-- Volta ao formato da 005: só ficam as marcas que eram dúvida do validador (descartada ou perto do limiar).

CREATE TABLE duvidas_dor_antiga (
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

INSERT INTO duvidas_dor_antiga
SELECT id, sessao_id, confirmacao_id,
       CASE WHEN ABS(veredito_dor_relativa - 3.5) <= 1.0 THEN 'perto_do_limiar' ELSE 'suspeita_descartada' END,
       criado_em, duracao_s, quadros, veredito_face, veredito_dor_relativa,
       face_classificada, categoria, observacao, classificada_em
  FROM duvidas_dor
 WHERE confirmacao_id IS NOT NULL
   AND (veredito = 'descartada' OR ABS(veredito_dor_relativa - 3.5) <= 1.0);

DROP INDEX IF EXISTS ix_duvidas_dor_pendentes;
DROP TABLE duvidas_dor;
ALTER TABLE duvidas_dor_antiga RENAME TO duvidas_dor;
CREATE INDEX IF NOT EXISTS ix_duvidas_dor_pendentes ON duvidas_dor(classificada_em, criado_em);
DELETE FROM schema_migrations WHERE id = '006_marcas_de_atencao';
