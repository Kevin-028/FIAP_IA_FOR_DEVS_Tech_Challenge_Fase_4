"""Caminhos do projeto Fase 4."""
from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOSPITAL_DATA = os.path.join(ROOT, "hospital_data")
DB_PATH = os.path.join(HOSPITAL_DATA, "hospital.db")
MODELS_DIR = os.path.join(ROOT, "models")
