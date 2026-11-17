DROP INDEX IF EXISTS ix_duvidas_dor_pendentes;
DROP TABLE IF EXISTS duvidas_dor;
DELETE FROM schema_migrations WHERE id = '005_duvidas_dor';
