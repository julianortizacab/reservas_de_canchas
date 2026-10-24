import pytest

from flaskr.inicializarBD import cargar_datos_semilla, crear_tablas
from flaskr.infrastructure.db.engine import crear_engine
from flaskr.infrastructure.db.session import crear_session_factory


@pytest.fixture
def session():
    """Sesión sobre SQLite en memoria, con datos semilla."""
    engine = crear_engine("sqlite:///:memory:")
    crear_tablas(engine)
    with crear_session_factory(engine)() as s:
        cargar_datos_semilla(s)
        yield s
    engine.dispose()


@pytest.fixture
def app():
    from flaskr import create_app

    app = create_app("test")
    with app.extensions["session_factory"]() as s:
        cargar_datos_semilla(s)
    yield app
    app.extensions["engine"].dispose()


@pytest.fixture
def client(app):
    return app.test_client()
