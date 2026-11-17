"""Caminhos do projeto Fase 4. FASE4_ROOT sobrepõe a raiz (ex.: app instalado fora do repositório)."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = os.environ.get("FASE4_ROOT") or str(Path(__file__).resolve().parents[3])
HOSPITAL_DATA = os.path.join(ROOT, "hospital_data")
DB_PATH = os.path.join(HOSPITAL_DATA, "hospital.db")
MODELS_DIR = os.path.join(ROOT, "models")
