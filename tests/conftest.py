"""
tests/conftest.py -- fixtures compartidas por toda la suite pytest.
"""
from __future__ import annotations

import pytest

from server import persistence


@pytest.fixture(autouse=True)
def _directorio_persistencia_aislado(tmp_path, monkeypatch):
    """
    Redirige ``server.persistence.DATA_DIR`` a un directorio temporal para
    cada prueba. Sin esto, cualquier prueba que pase por ``RoomManager``
    (que persiste en disco en cada mutación desde la Milestone 6) escribiría
    archivos ``.pkl`` reales en el ``data/games/`` del propio repositorio.
    """
    monkeypatch.setattr(persistence, "DATA_DIR", tmp_path / "games")
