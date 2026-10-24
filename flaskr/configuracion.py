"""Configuración por entorno, leída de variables de entorno (ver .env.example)."""
import os


class Config:
    TESTING = False
    DEBUG = False

    def __init__(self):
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///reservas.db")
        self.HORA_APERTURA = int(os.getenv("HORA_APERTURA", "8"))
        self.HORA_CIERRE = int(os.getenv("HORA_CIERRE", "22"))
        self.ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


class DevConfig(Config):
    DEBUG = True


class TestConfig(Config):
    __test__ = False  # evita que pytest lo tome por una clase de tests
    TESTING = True

    def __init__(self):
        super().__init__()
        self.DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")


CONFIGURACIONES = {"dev": DevConfig, "test": TestConfig}


def obtener_config(nombre: str | None = None) -> Config:
    """Devuelve la configuración de `nombre` o, si falta, de APP_ENV (por defecto 'dev')."""
    nombre = (nombre or os.getenv("APP_ENV", "dev")).lower()
    if nombre not in CONFIGURACIONES:
        raise ValueError(f"Entorno desconocido '{nombre}'. Usa: {', '.join(CONFIGURACIONES)}")
    return CONFIGURACIONES[nombre]()
