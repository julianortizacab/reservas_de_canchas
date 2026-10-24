from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from flaskr.infrastructure.db.engine import Base


class UsuarioOrm(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20))
