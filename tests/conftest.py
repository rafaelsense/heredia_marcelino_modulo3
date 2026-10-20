import pytest

from agente_logistico import servicios
from agente_logistico.inicializar_datos import inicializar_bd


@pytest.fixture
def bd_temporal(tmp_path, monkeypatch):
    """Crea una base aislada y redirige los servicios hacia ella."""
    ruta = inicializar_bd(tmp_path / "logistica.db")
    monkeypatch.setattr(servicios, "RUTA_BD", ruta)
    return ruta
