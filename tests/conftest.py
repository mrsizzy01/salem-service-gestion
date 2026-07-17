"""Configuration pytest : base de données temporaire isolée par test."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Rend le paquet ``app`` importable depuis la racine du projet.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    """Fournit une base SQLite vierge dans un dossier temporaire."""
    monkeypatch.setenv("GESTION_DATA_DIR", str(tmp_path / "data"))

    from app.models.database import init_engine, reset_engine
    from app.models.migrations import run_migrations

    reset_engine()
    engine = init_engine()
    run_migrations(engine)
    yield engine
    reset_engine()
