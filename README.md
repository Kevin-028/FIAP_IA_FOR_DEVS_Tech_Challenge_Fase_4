# Tech Challenge — Fase 4 | FIAP
### Consultório multimodal: conversa ao vivo, dor facial (Wong-Baker), vídeo, áudio e anomalias

Sistema de apoio à consulta e ao plantão. Na consulta, transcreve a conversa (Azure Speech), identifica médico e paciente, marca pontos de atenção (regras clínicas + Azure Language), monta o resumo clínico e estima a dor pelo rosto em cascata (MediaPipe no navegador → Py-Feat local), na escala de faces **Wong-Baker**. Na internação, analisa vídeo (MediaPipe Pose + YOLOv8), áudio (traços vocais + Azure), sinais vitais do PhysioNet (regras + Isolation Forest) e simula a leitura de um exame ao vivo. Tudo cai em uma caixa única de alertas.

Pacientes de internação de demonstração: `p000057` (estável) e `p000003` (sinais fora da faixa).

> Demo educacional. Dados PhysioNet/sintéticos — não usar com paciente real. Não substitui avaliação médica, não emite diagnóstico e não prescreve.

---

## Estrutura do projeto

```text
Fase_4/
├── src/
│   ├── Domain/          domain/{atendimento, anomalia, plantao}        regras e agregados (só biblioteca padrão)
│   ├── Application/     application/{atendimento, anomalia, plantao}   casos de uso e portas
│   ├── Infrastructure/  infrastructure/{persistencia, ia, azure, physionet}
│   └── Web/             web/{controllers, models, views, static}       MVC em Flask (dependencias.py monta tudo)
├── tests/               unit/{domain, application} · integration/{infrastructure, web} · test_arquitetura.py
├── scripts/             downloads de modelos e da base PhysioNet, áudio de demonstração
├── analises/            avaliação offline (números do relatório) e notebooks
├── hospital_data/       banco SQLite, registros PhysioNet, recortes das marcas de atenção (gerado)
└── models/              pesos baixados: pose, yolo, feat (gerado, fora do git)
```

---

## Pré-requisitos

- **Python 3.11+** e `pip` (desenvolvido com 3.12); CPU é suficiente, sem GPU
- **Chrome ou Edge** para a consulta ao vivo (microfone e câmera só em `localhost` ou https)
- **Internet** na primeira execução: dependências, pesos dos modelos e MediaPipe Face (via CDN)
- **Azure** (opcional): recursos *Speech* e *Language*. Sem eles, a fala pode ser digitada
- **Disco:** ~2 GB; +~1 GB com o estágio 2 da dor (Py-Feat + torch)

---

## Como rodar (do zero)

### 1. Ambiente virtual

```powershell
# Na pasta Fase_4/
python -m venv .venv

# Windows
.\.venv\Scripts\Activate.ps1

# Linux / macOS
# source .venv/bin/activate
```

### 2. Dependências

```powershell
pip install -r requirements.txt            # os quatro projetos (modo editável) + pytest

# Opcional: estágio 2 da dor facial (Py-Feat, ~1 GB)
pip install -r requirements-estagio2.txt
```

### 3. Configurar o `.env`

```powershell
Copy-Item .env.example .env      # Linux/macOS: cp .env.example .env
```

| Variável | Para quê | Obrigatória |
|---|---|---|
| `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` | Transcrição da conversa e do áudio | Não (sem ela, digite as falas) |
| `AZURE_LANGUAGE_KEY`, `AZURE_LANGUAGE_ENDPOINT` | Sentimento e frases-chave | Não |
| `ESTAGIO2_DETECTOR` | `v2` (padrão) ou `v1` do Py-Feat | Não |
| `ESTAGIO2_OCIOSIDADE_S` | Segundos sem uso até liberar o Py-Feat da memória (padrão 120) | Não |
| `ESTAGIO2_DESLIGADO` | `1` força só o estágio 1 da dor | Não |

### 4. Modelos e dados de demonstração

```powershell
python scripts/download_pose.py                # MediaPipe Pose (vídeo)
python scripts/download_yolo.py                # YOLOv8n (vídeo)
python scripts/make_demo_audio.py              # áudio de exemplo
python -c "from infrastructure.physionet.challenge2019 import save_choice; save_choice()"
python -m infrastructure.persistencia.seed     # pacientes de internação no banco
```

Os pesos do Py-Feat são baixados sozinhos para `models/feat/` na primeira confirmação de dor. Base PhysioNet completa (~40 mil registros, para treinar o modelo de anomalia): `python scripts/download_challenge2019.py`.

### 5. Subir a aplicação

```powershell
python -m web.app
```

Abra **http://127.0.0.1:5000** no Chrome ou Edge. No VS Code: **Run and Debug → Web: Fase 4 (Flask)**. O banco e as migrações são aplicados sozinhos na primeira requisição.

---

## Rotas principais

| Rota | Para que serve |
| --- | --- |
| `/` **Hoje** | Consultas em andamento, alertas que pedem ação, busca de paciente |
| `/pacientes` · `/pacientes/<id>` | Busca, cadastro e ficha com histórico e relatórios |
| `/consulta/<id>/preparar` | Etapa 1: aviso ao paciente, teste de microfone e câmera |
| `/consulta/<id>` | Etapa 2: conversa ao vivo, resumo clínico, câmera, dor Wong-Baker e alertas |
| `/consulta/<id>/encerrar` · `/relatorio` | Etapa 3: revisão, encerramento e relatório para imprimir |
| `/alertas` | Caixa única: consultas, internação e anomalia de padrão |
| `/revisao` | Marcas de atenção da dor: cada suspeita acima do nível 5 gravada (2 s antes e 2 s depois), veredito do validador como apoio, classificação do médico |
| `/internacao` | Painel do internado, exames de vídeo/áudio e exame ao vivo |
| `/sistema` | Estado do Azure, Py-Feat e modelos; treino do modelo de anomalia |

---

## Configurações da UI

- **Tema:** seletor **Auto · Claro · Escuro** no rodapé do menu (no celular, no topo). *Auto* segue o sistema; a escolha fica salva no navegador.
- **Microfone e câmera:** use `http://127.0.0.1:5000` ou `http://localhost:5000`. Se aparecer *Permission denied*: cadeado do endereço → Permitir; no Windows, *Configurações → Privacidade e segurança → Microfone/Câmera*.

---

## Testes automatizados

| Suíte | Pasta | Comando |
| --- | --- | --- |
| Arquitetura (referências entre projetos) | `tests/test_arquitetura.py` | `python -m pytest tests/test_arquitetura.py` |
| Unitários (domínio e casos de uso, sem banco/rede/modelo) | `tests/unit` | `python -m pytest tests/unit` |
| Integração (SQLite, modelos reais se instalados, rotas) | `tests/integration` | `python -m pytest tests/integration` |
| Azure real (pulado por padrão; usa o `.env`) | `tests/integration/infrastructure/test_azure_real.py` | `python -m pytest -m azure --azure` |
| Cobertura (`htmlcov/`) | — | `python -m pytest --cov --cov-report=html` |

---

## Problemas comuns

| Sintoma | O que fazer |
|---------|-------------|
| `ModuleNotFoundError: web` / `injector` / `domain` | Ativar o `.venv` e rodar `pip install -r requirements.txt` em `Fase_4/` |
| Internação sem pacientes / "Registro não encontrado" | `python -m infrastructure.persistencia.seed` |
| Vídeo com aviso "Peso … ausente" | `python scripts/download_pose.py` e `python scripts/download_yolo.py` |
| Conversa não transcreve / token 503 | Preencher `AZURE_SPEECH_*` no `.env` e reiniciar; ou digitar as falas |
| Microfone/câmera bloqueados | Abrir em `localhost` no Chrome/Edge e liberar a permissão |
| Dor não é confirmada | `pip install -r requirements-estagio2.txt`; a tela **Sistema** mostra o que falta |
| Modelo facial não carrega | O MediaPipe Face vem de CDN: precisa de internet na primeira carga |
| "Amostra ausente" no áudio | `python scripts/make_demo_audio.py` |
| Treino diz "corpus insuficiente" | `python scripts/download_challenge2019.py` |
