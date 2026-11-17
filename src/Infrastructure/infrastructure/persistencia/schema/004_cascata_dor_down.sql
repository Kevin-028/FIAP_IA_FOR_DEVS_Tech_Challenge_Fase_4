DROP INDEX IF EXISTS ix_autorrelatos_dor_sessao;
DROP INDEX IF EXISTS ix_confirmacoes_dor_sessao;
DROP TABLE IF EXISTS autorrelatos_dor;
DROP TABLE IF EXISTS confirmacoes_dor;
ALTER TABLE leituras_face DROP COLUMN wong_baker;
DELETE FROM schema_migrations WHERE id = '004_cascata_dor';
