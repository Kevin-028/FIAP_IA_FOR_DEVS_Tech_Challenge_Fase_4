-- Persistência do consultório no SQLite já usado pelo Flask.
-- Aditiva: não altera patients, alerts, vitals, prescriptions,
-- movement_events nem modality_reports. Não copia essas linhas.
--
-- Agregado → tabela
--   Paciente                         → pacientes
--   Sessão                           → sessoes
--   Alerta de dor                    → alertas_dor
--   Alerta de anomalia               → alertas_anomalia
--   sinal apontado (valor do alerta) → alertas_anomalia_sinais
--   Modelo de anomalia               → artefatos_modelo
--
-- Sessão referencia paciente existente.
-- Alerta de dor referencia sessão.
-- Alerta de anomalia referencia série (texto) e artefato. Sem paciente.
-- Artefato não referencia paciente. O corpus continua arquivo de treino.
--
-- Sem índice único em pacientes.nome: homônimos são admitidos.
-- Índices:
--   ix_sessoes_paciente — histórico das sessões de um paciente.
--   ix_alertas_dor_sessao — métrica e relatório leem os alertas de uma sessão.
--   ix_alertas_anomalia_serie_modelo — leitura de anomalia por série e modelo.
--
-- Consulta a observar: sessão pela PK mais alertas_dor por ix_alertas_dor_sessao.
-- Medir com EXPLAIN QUERY PLAN. Degrada se alertas_dor for varrida por inteiro,
-- ou se pacientes passar a contar séries do corpus (COUNT deixa de ser o cadastro).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS pacientes (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessoes (
    id TEXT PRIMARY KEY,
    paciente_id TEXT NOT NULL REFERENCES pacientes(id) ON DELETE RESTRICT,
    estado TEXT NOT NULL CHECK (estado IN ('em_andamento', 'encerrada')),
    texto_fala TEXT NOT NULL DEFAULT '',
    termos_criticos TEXT NOT NULL DEFAULT '',
    sentimento TEXT NOT NULL DEFAULT '',
    alteracao_vocal TEXT NOT NULL DEFAULT '',
    postura TEXT NOT NULL DEFAULT '',
    face TEXT NOT NULL DEFAULT '',
    objetos_areas TEXT NOT NULL DEFAULT '',
    iniciada_em TEXT NOT NULL,
    encerrada_em TEXT
);

CREATE TABLE IF NOT EXISTS alertas_dor (
    id TEXT PRIMARY KEY,
    sessao_id TEXT NOT NULL REFERENCES sessoes(id) ON DELETE RESTRICT,
    origem TEXT NOT NULL CHECK (origem IN ('face', 'movimentacao', 'relato')),
    descricao_sinal TEXT,
    estado TEXT NOT NULL DEFAULT 'aberto' CHECK (estado IN ('aberto', 'ciente', 'encerrado')),
    criado_em TEXT NOT NULL,
    ciente_em TEXT,
    encerrado_em TEXT
);

CREATE TABLE IF NOT EXISTS artefatos_modelo (
    id TEXT PRIMARY KEY,
    treinado_no_corpus INTEGER NOT NULL CHECK (treinado_no_corpus = 1),
    formato TEXT NOT NULL,
    conteudo BLOB NOT NULL CHECK (length(conteudo) > 0),
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alertas_anomalia (
    id TEXT PRIMARY KEY,
    serie_id TEXT NOT NULL,
    modelo_id TEXT NOT NULL REFERENCES artefatos_modelo(id) ON DELETE RESTRICT,
    estado TEXT NOT NULL DEFAULT 'aberto' CHECK (estado IN ('aberto', 'ciente', 'encerrado')),
    criado_em TEXT NOT NULL,
    ciente_em TEXT,
    encerrado_em TEXT
);

CREATE TABLE IF NOT EXISTS alertas_anomalia_sinais (
    alerta_id TEXT NOT NULL REFERENCES alertas_anomalia(id) ON DELETE RESTRICT,
    sinal TEXT NOT NULL CHECK (sinal IN ('batimentos', 'pressao_arterial', 'oxigenacao')),
    PRIMARY KEY (alerta_id, sinal)
);

CREATE INDEX IF NOT EXISTS ix_sessoes_paciente ON sessoes(paciente_id);
CREATE INDEX IF NOT EXISTS ix_alertas_dor_sessao ON alertas_dor(sessao_id);
CREATE INDEX IF NOT EXISTS ix_alertas_anomalia_serie_modelo
    ON alertas_anomalia(serie_id, modelo_id);

CREATE TRIGGER IF NOT EXISTS pacientes_recusa_delete
BEFORE DELETE ON pacientes
BEGIN
    SELECT RAISE(ABORT, 'exclusao de paciente recusada');
END;

CREATE TRIGGER IF NOT EXISTS sessoes_recusa_delete
BEFORE DELETE ON sessoes
BEGIN
    SELECT RAISE(ABORT, 'exclusao de sessao recusada');
END;

CREATE TRIGGER IF NOT EXISTS alertas_dor_recusa_delete
BEFORE DELETE ON alertas_dor
BEGIN
    SELECT RAISE(ABORT, 'exclusao de alerta de dor recusada');
END;

CREATE TRIGGER IF NOT EXISTS alertas_anomalia_recusa_delete
BEFORE DELETE ON alertas_anomalia
BEGIN
    SELECT RAISE(ABORT, 'exclusao de alerta de anomalia recusada');
END;

CREATE TRIGGER IF NOT EXISTS alertas_anomalia_sinais_recusa_delete
BEFORE DELETE ON alertas_anomalia_sinais
BEGIN
    SELECT RAISE(ABORT, 'exclusao de sinal de anomalia recusada');
END;
