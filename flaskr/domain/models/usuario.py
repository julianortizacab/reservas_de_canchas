from dataclasses import dataclass
from enum import Enum


class Rol(str, Enum):
    ADMIN = "admin"
    OPERADOR = "operador"


@dataclass
class Usuario:
    id: int | None
    username: str
    password_hash: str
    rol: Rol
