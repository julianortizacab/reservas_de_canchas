from dataclasses import dataclass


@dataclass
class Cliente:
    id: int | None
    nombre: str
    documento: str
    telefono: str
    email: str
