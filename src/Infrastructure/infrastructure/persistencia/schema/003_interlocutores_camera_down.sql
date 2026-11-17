DROP TRIGGER IF EXISTS eventos_face_recusa_delete;
DROP INDEX IF EXISTS ix_eventos_face_sessao;
DROP INDEX IF EXISTS ix_leituras_face_sessao;
DROP TABLE IF EXISTS eventos_face;
DROP TABLE IF EXISTS leituras_face;
ALTER TABLE falas DROP COLUMN expressao_face;
ALTER TABLE sessao_locutores DROP COLUMN confianca;
ALTER TABLE sessao_locutores DROP COLUMN origem;
DELETE FROM schema_migrations WHERE id = '003_interlocutores_camera';
