-- Papel automático do locutor e análise facial em tempo real.
-- Aditiva: colunas novas com valor padrão e duas tabelas novas.
--
--   sessao_locutores.origem     'manual' (médico corrigiu) ou 'auto' (classificador)
--   sessao_locutores.confianca  0.5..0.99 quando automático
--   falas.expressao_face        expressão do rosto no momento da fala
--   leituras_face               uma leitura por segundo (blendshapes → expressão e PSPI)
--   eventos_face                mudança estável de expressão ou dor sustentada (entram na conversa)
--
-- Nenhuma imagem é gravada: só os números derivados do rosto.

ALTER TABLE sessao_locutores ADD COLUMN origem TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE sessao_locutores ADD COLUMN confianca REAL;
ALTER TABLE falas ADD COLUMN expressao_face TEXT NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS leituras_face (
    id TEXT PRIMARY KEY,
    sessao_id TEXT NOT NULL REFERENCES sessoes(id) ON DELETE RESTRICT,
    registrado_em TEXT NOT NULL,
    expressao TEXT NOT NULL,
    valencia TEXT NOT NULL CHECK (valencia IN ('positiva', 'neutra', 'negativa')),
    dor_pspi REAL NOT NULL,
    dor_relativa REAL NOT NULL,
    nivel_dor TEXT NOT NULL CHECK (nivel_dor IN ('ausente', 'leve', 'moderada')),
    scores TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eventos_face (
    id TEXT PRIMARY KEY,
    sessao_id TEXT NOT NULL REFERENCES sessoes(id) ON DELETE RESTRICT,
    registrado_em TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('expressao', 'dor')),
    expressao TEXT NOT NULL,
    descricao TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_leituras_face_sessao ON leituras_face(sessao_id, registrado_em);
CREATE INDEX IF NOT EXISTS ix_eventos_face_sessao ON eventos_face(sessao_id, registrado_em);

CREATE TRIGGER IF NOT EXISTS eventos_face_recusa_delete
BEFORE DELETE ON eventos_face
BEGIN
    SELECT RAISE(ABORT, 'exclusao de evento facial recusada');
END;
