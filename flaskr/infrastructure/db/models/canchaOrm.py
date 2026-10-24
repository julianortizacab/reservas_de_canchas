from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from flaskr.infrastructure.db.engine import Base


class CanchaOrm(Base):
    __tablename__ = "canchas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    deporte: Mapped[str] = mapped_column(String(20))
    precio_hora: Mapped[float]
    activa: Mapped[bool] = mapped_column(default=True)
