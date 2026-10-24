from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class EstadoReserva(str, Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    CANCELADA = "CANCELADA"
    COMPLETADA = "COMPLETADA"


@dataclass(kw_only=True)
class Reserva:
    id: int | None = None
    cancha_id: int
    cliente_id: int
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: EstadoReserva = EstadoReserva.PENDIENTE
    total: float = 0.0


@dataclass(frozen=True)
class CotizacionReserva:
    cancha_id: int
    fecha_inicio: datetime
    fecha_fin: datetime
    duracion: timedelta
    precio_hora: float
    total: float


# --- Excepciones de dominio (el controlador las traduce a 400 / 404 / 409) ---
class ReservaInvalida(Exception):
    """Datos o transición de estado que violan una regla de negocio (400)."""


class ReservaNoEncontrada(Exception):
    """El recurso solicitado no existe (404)."""


class CanchaNoEncontrada(ReservaNoEncontrada):
    pass


class ClienteNoEncontrado(ReservaNoEncontrada):
    pass


class CanchaNoDisponible(Exception):
    """Cancha inactiva o con cruce de horario (409)."""
