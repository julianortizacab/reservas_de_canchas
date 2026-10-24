"""Adaptador de salida: implementa el puerto ReservaRepository con SQLAlchemy.

El mapeo ORM <-> dominio vive aquí; el dominio nunca ve el ORM.
"""
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from flaskr.domain.models.cancha import Cancha, Deporte
from flaskr.domain.models.cliente import Cliente
from flaskr.domain.models.reserva import EstadoReserva, Reserva, ReservaNoEncontrada
from flaskr.domain.repositories.reservaRepository import ReservaRepository
from flaskr.infrastructure.db.models.canchaOrm import CanchaOrm
from flaskr.infrastructure.db.models.clienteOrm import ClienteOrm
from flaskr.infrastructure.db.models.reservaOrm import ReservaOrm


def _reserva_a_dominio(o: ReservaOrm) -> Reserva:
    return Reserva(
        id=o.id,
        cancha_id=o.cancha_id,
        cliente_id=o.cliente_id,
        fecha_inicio=o.fecha_inicio,
        fecha_fin=o.fecha_fin,
        estado=EstadoReserva(o.estado),
        total=o.total,
    )


def _copiar_a_orm(r: Reserva, o: ReservaOrm) -> ReservaOrm:
    o.cancha_id = r.cancha_id
    o.cliente_id = r.cliente_id
    o.fecha_inicio = r.fecha_inicio
    o.fecha_fin = r.fecha_fin
    o.estado = r.estado.value
    o.total = r.total
    return o


class ReservaRepositorySQL(ReservaRepository):
    def __init__(self, session: Session):
        self._session = session

    def guardar(self, reserva: Reserva) -> Reserva:
        orm = _copiar_a_orm(reserva, ReservaOrm())
        self._session.add(orm)
        self._session.commit()
        return _reserva_a_dominio(orm)

    def obtener_por_id(self, reserva_id: int) -> Reserva | None:
        orm = self._session.get(ReservaOrm, reserva_id)
        return _reserva_a_dominio(orm) if orm else None

    def listar(
        self,
        cancha_id: int | None = None,
        cliente_id: int | None = None,
        fecha: date | None = None,
        estado: EstadoReserva | None = None,
    ) -> list[Reserva]:
        consulta = select(ReservaOrm).order_by(ReservaOrm.fecha_inicio, ReservaOrm.id)
        if cancha_id is not None:
            consulta = consulta.where(ReservaOrm.cancha_id == cancha_id)
        if cliente_id is not None:
            consulta = consulta.where(ReservaOrm.cliente_id == cliente_id)
        if fecha is not None:
            desde = datetime.combine(fecha, time.min)
            consulta = consulta.where(
                ReservaOrm.fecha_inicio >= desde,
                ReservaOrm.fecha_inicio < desde + timedelta(days=1),
            )
        if estado is not None:
            consulta = consulta.where(ReservaOrm.estado == estado.value)
        return [_reserva_a_dominio(o) for o in self._session.scalars(consulta)]

    def buscar_cruces(self, cancha_id: int, inicio: datetime, fin: datetime) -> list[Reserva]:
        consulta = select(ReservaOrm).where(
            ReservaOrm.cancha_id == cancha_id,
            ReservaOrm.estado != EstadoReserva.CANCELADA.value,
            ReservaOrm.fecha_inicio < fin,
            ReservaOrm.fecha_fin > inicio,
        )
        return [_reserva_a_dominio(o) for o in self._session.scalars(consulta)]

    def actualizar(self, reserva: Reserva) -> Reserva:
        orm = self._session.get(ReservaOrm, reserva.id)
        if orm is None:
            raise ReservaNoEncontrada(f"La reserva {reserva.id} no existe")
        _copiar_a_orm(reserva, orm)
        self._session.commit()
        return _reserva_a_dominio(orm)

    def obtener_cancha(self, cancha_id: int) -> Cancha | None:
        o = self._session.get(CanchaOrm, cancha_id)
        if o is None:
            return None
        return Cancha(o.id, o.nombre, Deporte(o.deporte), o.precio_hora, o.activa)

    def obtener_cliente(self, cliente_id: int) -> Cliente | None:
        o = self._session.get(ClienteOrm, cliente_id)
        if o is None:
            return None
        return Cliente(o.id, o.nombre, o.documento, o.telefono, o.email)

    def listar_canchas(self, deporte: Deporte | None = None) -> list[Cancha]:
        consulta = select(CanchaOrm).where(CanchaOrm.activa.is_(True)).order_by(CanchaOrm.nombre)
        if deporte is not None:
            consulta = consulta.where(CanchaOrm.deporte == deporte.value)
        return [
            Cancha(o.id, o.nombre, Deporte(o.deporte), o.precio_hora, o.activa)
            for o in self._session.scalars(consulta)
        ]

    def buscar_clientes(self, texto: str) -> list[Cliente]:
        patron = f"%{texto.strip()}%"
        consulta = (
            select(ClienteOrm)
            .where(
                ClienteOrm.nombre.ilike(patron)
                | ClienteOrm.documento.ilike(patron)
            )
            .order_by(ClienteOrm.nombre)
        )
        return [
            Cliente(o.id, o.nombre, o.documento, o.telefono, o.email)
            for o in self._session.scalars(consulta)
        ]
