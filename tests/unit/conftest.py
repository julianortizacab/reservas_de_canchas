from dataclasses import replace
from datetime import datetime

import pytest

from flaskr.domain.models.cancha import Cancha, Deporte
from flaskr.domain.models.cliente import Cliente
from flaskr.domain.models.reserva import EstadoReserva
from flaskr.repositories.reservaRepository import ReservaRepository
from flaskr.services.reservaServices import ReservaService

AHORA = datetime(2030, 1, 15, 9, 0)


class RepositorioFake(ReservaRepository):
    """Repositorio en memoria; devuelve copias para imitar una BD real."""

    def __init__(self):
        self.reservas = {}
        self.canchas = {}
        self.clientes = {}
        self._seq = 0

    def guardar(self, reserva):
        self._seq += 1
        guardada = replace(reserva, id=self._seq)
        self.reservas[guardada.id] = guardada
        return replace(guardada)

    def obtener_por_id(self, reserva_id):
        r = self.reservas.get(reserva_id)
        return replace(r) if r else None

    def listar(self, cancha_id=None, cliente_id=None, fecha=None, estado=None):
        return [
            replace(r)
            for r in self.reservas.values()
            if (cancha_id is None or r.cancha_id == cancha_id)
            and (cliente_id is None or r.cliente_id == cliente_id)
            and (fecha is None or r.fecha_inicio.date() == fecha)
            and (estado is None or r.estado is estado)
        ]

    def buscar_cruces(self, cancha_id, inicio, fin):
        return [
            replace(r)
            for r in self.reservas.values()
            if r.cancha_id == cancha_id
            and r.estado is not EstadoReserva.CANCELADA
            and r.fecha_inicio < fin
            and r.fecha_fin > inicio
        ]

    def actualizar(self, reserva):
        self.reservas[reserva.id] = replace(reserva)
        return replace(reserva)

    def obtener_cancha(self, cancha_id):
        return self.canchas.get(cancha_id)

    def obtener_cliente(self, cliente_id):
        return self.clientes.get(cliente_id)

    def listar_canchas(self, deporte=None):
        return [
            cancha
            for cancha in self.canchas.values()
            if cancha.activa and (deporte is None or cancha.deporte is deporte)
        ]

    def buscar_clientes(self, texto):
        termino = texto.casefold()
        return [
            cliente
            for cliente in self.clientes.values()
            if termino in cliente.nombre.casefold() or termino in cliente.documento.casefold()
        ]


class Reloj:
    def __init__(self, ahora):
        self.ahora = ahora

    def __call__(self):
        return self.ahora


@pytest.fixture
def ahora():
    return AHORA


@pytest.fixture
def reloj():
    return Reloj(AHORA)


@pytest.fixture
def repo():
    r = RepositorioFake()
    r.canchas[1] = Cancha(1, "Fútbol 1", Deporte.FUTBOL, 100.0, True)
    r.canchas[2] = Cancha(2, "Tenis 1", Deporte.TENIS, 80.0, False)  # inactiva
    r.canchas[3] = Cancha(3, "Pádel 1", Deporte.PADEL, 60.0, True)
    r.clientes[1] = Cliente(1, "Ana", "111", "300", "ana@x.com")
    r.clientes[2] = Cliente(2, "Luis", "222", "301", "luis@x.com")
    return r


@pytest.fixture
def servicio(repo, reloj):
    return ReservaService(repo, ahora=reloj)
