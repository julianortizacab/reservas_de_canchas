from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """Base declarativa de todos los modelos ORM."""


def crear_engine(url: str) -> Engine:
    if not url.startswith("sqlite"):
        return create_engine(url)
    opciones = {"connect_args": {"check_same_thread": False}}
    if url == "sqlite://" or ":memory:" in url:
        # una sola conexión compartida: si no, cada conexión vería una BD vacía distinta
        opciones["poolclass"] = StaticPool
    return create_engine(url, **opciones)
