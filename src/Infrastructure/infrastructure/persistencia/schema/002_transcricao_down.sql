DROP TRIGGER IF EXISTS pontos_atencao_recusa_delete;
DROP TRIGGER IF EXISTS falas_recusa_delete;
DROP INDEX IF EXISTS ix_pontos_atencao_sessao;
DROP INDEX IF EXISTS ix_falas_sessao;
DROP TABLE IF EXISTS pontos_atencao;
DROP TABLE IF EXISTS sessao_locutores;
DROP TABLE IF EXISTS falas;
DELETE FROM schema_migrations WHERE id = '002_transcricao';
