from dataclasses import dataclass
from enum import Enum


class Deporte(str, Enum):
    FUTBOL = "futbol"
    TENIS = "tenis"
    BALONCESTO = "baloncesto"
    PADEL = "padel"


@dataclass
class Cancha:
    id: int | None
    nombre: str
    deporte: Deporte
    precio_hora: float
    activa: bool = True
