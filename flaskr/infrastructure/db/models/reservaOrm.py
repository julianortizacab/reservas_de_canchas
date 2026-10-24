from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from flaskr.infrastructure.db.engine import Base


class ReservaOrm(Base):
    __tablename__ = "reservas"
    __table_args__ = (Index("ix_reservas_cancha_inicio", "cancha_id", "fecha_inicio"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cancha_id: Mapped[int] = mapped_column(ForeignKey("canchas.id"))
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    fecha_inicio: Mapped[datetime]
    fecha_fin: Mapped[datetime]
    estado: Mapped[str] = mapped_column(String(20))
    total: Mapped[float]
