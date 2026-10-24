from datetime import date, datetime

import pytest
from sqlalchemy import select
from werkzeug.security import check_password_hash

from flaskr.domain.models.cancha import Deporte
from flaskr.domain.models.reserva import EstadoReserva, Reserva, ReservaNoEncontrada
from flaskr.inicializarBD import cargar_datos_semilla
from flaskr.infrastructure.adaptadorSalida.reservaRepositorySQL import ReservaRepositorySQL
from flaskr.infrastructure.db.models.canchaOrm import CanchaOrm
from flaskr.infrastructure.db.models.clienteOrm import ClienteOrm
from flaskr.infrastructure.db.models.usuarioOrm import UsuarioOrm


@pytest.fixture
def repo(session):
    return ReservaRepositorySQL(session)


def nueva(cancha=1, cliente=1, ini=(2030, 1, 16, 10), fin=(2030, 1, 16, 12)):
    return Reserva(cancha_id=cancha, cliente_id=cliente,
                   fecha_inicio=datetime(*ini), fecha_fin=datetime(*fin), total=100.0)


def test_semilla_y_idempotencia(session):
    assert len(session.scalars(select(CanchaOrm)).all()) == 4
    assert len(session.scalars(select(ClienteOrm)).all()) == 3
    admin = session.scalars(select(UsuarioOrm)).one()
    assert admin.rol == "admin" and check_password_hash(admin.password_hash, "admin123")
    assert cargar_datos_semilla(session) is False
    assert len(session.scalars(select(CanchaOrm)).all()) == 4


def test_obtener_cancha_y_cliente(repo):
    cancha = repo.obtener_cancha(1)
    assert cancha.deporte is Deporte.FUTBOL and cancha.activa
    assert repo.obtener_cancha(99) is None
    assert repo.obtener_cliente(1).nombre == "Ana Gómez"
    assert repo.obtener_cliente(99) is None


def test_listar_canchas_activas_y_buscar_clientes(repo):
    canchas = repo.listar_canchas()
    assert all(cancha.activa for cancha in canchas)
    assert [cancha.nombre for cancha in repo.listar_canchas(Deporte.TENIS)] == [
        "Tenis - Cancha Central"
    ]
    assert [cliente.nombre for cliente in repo.buscar_clientes("ana")] == ["Ana Gómez"]
    assert [cliente.nombre for cliente in repo.buscar_clientes("1010101010")] == ["Ana Gómez"]


def test_guardar_y_obtener(repo):
    guardada = repo.guardar(nueva())
    assert guardada.id is not None
    assert repo.obtener_por_id(guardada.id) == guardada
    assert repo.obtener_por_id(999) is None


def test_actualizar(repo):
    r = repo.guardar(nueva())
    r.estado = EstadoReserva.CONFIRMADA
    assert repo.actualizar(r).estado is EstadoReserva.CONFIRMADA
    assert repo.obtener_por_id(r.id).estado is EstadoReserva.CONFIRMADA


def test_actualizar_inexistente(repo):
    r = nueva()
    r.id = 999
    with pytest.raises(ReservaNoEncontrada):
        repo.actualizar(r)


def test_listar_con_filtros(repo):
    a = repo.guardar(nueva())
    repo.guardar(nueva(cancha=2, cliente=2, ini=(2030, 1, 17, 10), fin=(2030, 1, 17, 11)))
    a.estado = EstadoReserva.CONFIRMADA
    repo.actualizar(a)
    assert len(repo.listar()) == 2
    assert [r.id for r in repo.listar(cancha_id=1)] == [a.id]
    assert len(repo.listar(cliente_id=2)) == 1
    assert len(repo.listar(fecha=date(2030, 1, 17))) == 1
    assert len(repo.listar(estado=EstadoReserva.CONFIRMADA)) == 1
    assert repo.listar(cancha_id=1, estado=EstadoReserva.PENDIENTE) == []


def test_buscar_cruces(repo):
    r = repo.guardar(nueva())
    d = lambda h: datetime(2030, 1, 16, h)
    assert [x.id for x in repo.buscar_cruces(1, d(11), d(13))] == [r.id]
    assert repo.buscar_cruces(1, d(12), d(14)) == []   # contigua: no cruza
    assert repo.buscar_cruces(2, d(10), d(12)) == []   # otra cancha
    r.estado = EstadoReserva.CANCELADA
    repo.actualizar(r)
    assert repo.buscar_cruces(1, d(10), d(12)) == []   # cancelada: no bloquea
