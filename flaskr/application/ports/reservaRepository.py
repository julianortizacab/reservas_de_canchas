"""Compatibilidad: el contrato de repositorio vive en el dominio."""
from flaskr.domain.repositories.reservaRepository import ReservaRepository

__all__ = ["ReservaRepository"]
