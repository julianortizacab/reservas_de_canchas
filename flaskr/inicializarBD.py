"""Crea las tablas y carga datos semilla.  Uso:  python -m flaskr.inicializarBD"""
from dotenv import load_dotenv
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

from flaskr.configuracion import obtener_config
from flaskr.domain.models.cancha import Deporte
from flaskr.domain.models.usuario import Rol
from flaskr.infrastructure.db.engine import Base, crear_engine
from flaskr.infrastructure.db.models.canchaOrm import CanchaOrm
from flaskr.infrastructure.db.models.clienteOrm import ClienteOrm
from flaskr.infrastructure.db.models.reservaOrm import ReservaOrm  # noqa: F401  (registra la tabla)
from flaskr.infrastructure.db.models.usuarioOrm import UsuarioOrm
from flaskr.infrastructure.db.session import crear_session_factory


def crear_tablas(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def cargar_datos_semilla(session: Session, admin_password: str = "admin123") -> bool:
    """Siembra 4 canchas, 3 clientes y 1 admin. Idempotente: devuelve False si ya había datos."""
    if session.scalar(select(func.count()).select_from(CanchaOrm)):
        return False
    session.add_all(
        [
            CanchaOrm(nombre="Fútbol 5 - Cancha A", deporte=Deporte.FUTBOL.value, precio_hora=80000, activa=True),
            CanchaOrm(nombre="Tenis - Cancha Central", deporte=Deporte.TENIS.value, precio_hora=40000, activa=True),
            CanchaOrm(nombre="Baloncesto - Cancha Techada", deporte=Deporte.BALONCESTO.value, precio_hora=50000, activa=True),
            CanchaOrm(nombre="Pádel - Cancha 1", deporte=Deporte.PADEL.value, precio_hora=60000, activa=True),
            ClienteOrm(nombre="Ana Gómez", documento="1010101010", telefono="3001112233", email="ana@example.com"),
            ClienteOrm(nombre="Luis Pérez", documento="2020202020", telefono="3004445566", email="luis@example.com"),
            ClienteOrm(nombre="María Rojas", documento="3030303030", telefono="3007778899", email="maria@example.com"),
            UsuarioOrm(username="admin", password_hash=generate_password_hash(admin_password), rol=Rol.ADMIN.value),
        ]
    )
    session.commit()
    return True


def main() -> None:
    load_dotenv()
    config = obtener_config()
    engine = crear_engine(config.DATABASE_URL)
    crear_tablas(engine)
    with crear_session_factory(engine)() as session:
        sembrado = cargar_datos_semilla(session, config.ADMIN_PASSWORD)
    print(f"Tablas creadas en {config.DATABASE_URL}.")
    print("Datos semilla cargados." if sembrado else "La BD ya tenía datos; no se sembró nada.")
    if sembrado and config.ADMIN_PASSWORD == "admin123":
        print("AVISO: usuario admin con la contraseña por defecto; define ADMIN_PASSWORD en .env.")


if __name__ == "__main__":
    main()
