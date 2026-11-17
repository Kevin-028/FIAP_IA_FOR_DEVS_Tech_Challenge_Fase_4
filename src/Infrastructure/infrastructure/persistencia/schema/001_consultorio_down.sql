-- Reverte só 001_consultorio. Não mexe nas tabelas já aplicadas do plantão.

PRAGMA foreign_keys = ON;

DROP TRIGGER IF EXISTS pacientes_recusa_delete;
DROP TRIGGER IF EXISTS sessoes_recusa_delete;
DROP TRIGGER IF EXISTS alertas_dor_recusa_delete;
DROP TRIGGER IF EXISTS alertas_anomalia_recusa_delete;
DROP TRIGGER IF EXISTS alertas_anomalia_sinais_recusa_delete;

DROP TABLE IF EXISTS alertas_anomalia_sinais;
DROP TABLE IF EXISTS alertas_anomalia;
DROP TABLE IF EXISTS alertas_dor;
DROP TABLE IF EXISTS sessoes;
DROP TABLE IF EXISTS artefatos_modelo;
DROP TABLE IF EXISTS pacientes;

DELETE FROM schema_migrations WHERE id = '001_consultorio';
