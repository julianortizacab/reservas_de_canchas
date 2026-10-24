import pytest

from flaskr.configuracion import DevConfig, TestConfig, obtener_config


def test_entornos(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    assert isinstance(obtener_config(), DevConfig)
    assert isinstance(obtener_config("test"), TestConfig)
    monkeypatch.setenv("APP_ENV", "test")
    assert isinstance(obtener_config(), TestConfig)


def test_variables_de_entorno(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///otra.db")
    monkeypatch.setenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("HORA_CIERRE", "20")
    assert obtener_config("dev").DATABASE_URL == "sqlite:///otra.db"
    assert obtener_config("dev").HORA_CIERRE == 20
    assert obtener_config("test").DATABASE_URL == "sqlite:///:memory:"


def test_entorno_desconocido():
    with pytest.raises(ValueError):
        obtener_config("prod")
