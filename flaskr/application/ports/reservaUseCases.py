from collections.abc import Callable
from datetime import date, datetime
from typing import Protocol

from flaskr.domain.models.cancha import Cancha, Deporte
from flaskr.domain.models.cliente import Cliente
from flaskr.domain.models.reserva import CotizacionReserva, EstadoReserva, Reserva


class ReservaUseCases(Protocol):
    def listar_canchas(self, deporte: Deporte | str | None = None) -> list[Cancha]: ...

    def buscar_cliente(self, texto: str) -> list[Cliente]: ...

    def cotizar_reserva(
        self, cancha_id: int, inicio: datetime, fin: datetime
    ) -> CotizacionReserva: ...

    def sugerir_horarios(
        self, cancha_id: int, fecha: date, duracion_horas: float
    ) -> list[tuple[datetime, datetime]]: ...

    def crear_reserva(
        self, cancha_id: int, cliente_id: int, inicio: datetime, fin: datetime
    ) -> Reserva: ...

    def confirmar_reserva(self, reserva_id: int) -> Reserva: ...

    def cancelar_reserva(self, reserva_id: int) -> Reserva: ...

    def completar_reserva(self, reserva_id: int) -> Reserva: ...

    def obtener_reserva(self, reserva_id: int) -> Reserva: ...

    def listar_reservas(
        self,
        cancha_id: int | None = None,
        cliente_id: int | None = None,
        fecha: date | None = None,
        estado: EstadoReserva | str | None = None,
    ) -> list[Reserva]: ...

    def consultar_disponibilidad(
        self, cancha_id: int, fecha: date
    ) -> list[tuple[datetime, datetime]]: ...


ReservaUseCasesFactory = Callable[[], ReservaUseCases]
