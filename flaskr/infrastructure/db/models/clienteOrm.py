from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from flaskr.infrastructure.db.engine import Base


class ClienteOrm(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    documento: Mapped[str] = mapped_column(String(30), unique=True)
    telefono: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(120))
