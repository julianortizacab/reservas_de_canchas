from collections.abc import Callable
from datetime import date, datetime, timedelta
from math import isfinite

from flaskr.domain.models.cancha import Cancha, Deporte
from flaskr.domain.models.cliente import Cliente
from flaskr.domain.models.reserva import (
    CanchaNoDisponible,
    CanchaNoEncontrada,
    ClienteNoEncontrado,
    CotizacionReserva,
    EstadoReserva,
    Reserva,
    ReservaInvalida,
    ReservaNoEncontrada,
)
from flaskr.domain.repositories.reservaRepository import ReservaRepository

Franja = tuple[datetime, datetime]


class ReservaService:
    DURACION_MINIMA = timedelta(hours=1)
    DURACION_MAXIMA = timedelta(hours=3)
    ANTICIPACION_CANCELACION = timedelta(hours=2)

    def __init__(
        self,
        repositorio: ReservaRepository,
        ahora: Callable[[], datetime] = datetime.now,
        hora_apertura: int = 8,
        hora_cierre: int = 22,
    ):
        self._repo = repositorio
        self._ahora = ahora
        self._apertura = hora_apertura
        self._cierre = hora_cierre

    # ---------------------------------------------------------------- crear
    def crear_reserva(
        self, cancha_id: int, cliente_id: int, inicio: datetime, fin: datetime
    ) -> Reserva:
        cancha = self._obtener_cancha_activa(cancha_id)
        if self._repo.obtener_cliente(cliente_id) is None:
            raise ClienteNoEncontrado(f"El cliente {cliente_id} no existe")
        cotizacion = self._cotizar_con_cancha(cancha_id, cancha, inicio, fin)
        reserva = Reserva(
            cancha_id=cancha_id,
            cliente_id=cliente_id,
            fecha_inicio=inicio,
            fecha_fin=fin,
            estado=EstadoReserva.PENDIENTE,
            total=cotizacion.total,
        )
        return self._repo.guardar(reserva)

    def listar_canchas(self, deporte: Deporte | str | None = None) -> list[Cancha]:
        if isinstance(deporte, str):
            try:
                deporte = Deporte(deporte.strip().lower())
            except ValueError as exc:
                validos = ", ".join(item.value for item in Deporte)
                raise ReservaInvalida(
                    f"Deporte inválido '{deporte}'. Valores permitidos: {validos}"
                ) from exc
        return self._repo.listar_canchas(deporte)

    def buscar_cliente(self, texto: str) -> list[Cliente]:
        if not texto.strip():
            raise ReservaInvalida("El texto de búsqueda de cliente no puede estar vacío")
        return self._repo.buscar_clientes(texto)

    def cotizar_reserva(
        self, cancha_id: int, inicio: datetime, fin: datetime
    ) -> CotizacionReserva:
        cancha = self._obtener_cancha_activa(cancha_id)
        return self._cotizar_con_cancha(cancha_id, cancha, inicio, fin)

    def _cotizar_con_cancha(
        self, cancha_id: int, cancha: Cancha, inicio: datetime, fin: datetime
    ) -> CotizacionReserva:
        if fin <= inicio:
            raise ReservaInvalida("La fecha de fin debe ser posterior a la de inicio")
        duracion = fin - inicio
        if duracion < self.DURACION_MINIMA:
            raise ReservaInvalida("La duración mínima de una reserva es 1 hora")
        if duracion > self.DURACION_MAXIMA:
            raise ReservaInvalida("La duración máxima de una reserva es 3 horas")
        if inicio < self._ahora():
            raise ReservaInvalida("No se pueden crear reservas en el pasado")
        if self._repo.buscar_cruces(cancha_id, inicio, fin):
            raise CanchaNoDisponible("La cancha ya está reservada en ese horario")
        total = round(duracion.total_seconds() / 3600 * cancha.precio_hora, 2)
        return CotizacionReserva(
            cancha_id=cancha_id,
            fecha_inicio=inicio,
            fecha_fin=fin,
            duracion=duracion,
            precio_hora=cancha.precio_hora,
            total=total,
        )

    def sugerir_horarios(
        self, cancha_id: int, fecha: date, duracion_horas: float
    ) -> list[tuple[datetime, datetime]]:
        if not isfinite(duracion_horas):
            raise ReservaInvalida("La duración debe ser un número entre 1 y 3 horas")
        duracion = timedelta(hours=duracion_horas)
        if duracion < self.DURACION_MINIMA or duracion > self.DURACION_MAXIMA:
            raise ReservaInvalida("La duración debe estar entre 1 y 3 horas")
        franjas = self.consultar_disponibilidad(cancha_id, fecha)
        sugerencias: list[tuple[datetime, datetime]] = []
        paso = timedelta(minutes=30)
        for libre_inicio, libre_fin in franjas:
            offset = libre_inicio - datetime.combine(fecha, datetime.min.time())
            minutos = offset.total_seconds() // 60
            inicio = datetime.combine(fecha, datetime.min.time()) + timedelta(
                minutes=((int(minutos) + 29) // 30) * 30
            )
            while inicio + duracion <= libre_fin and len(sugerencias) < 10:
                sugerencias.append((inicio, inicio + duracion))
                inicio += paso
            if len(sugerencias) == 10:
                break
        return sugerencias

    # ------------------------------------------------------ cambios de estado
    def confirmar_reserva(self, reserva_id: int) -> Reserva:
        reserva = self._obtener(reserva_id)
        if reserva.estado is not EstadoReserva.PENDIENTE:
            raise ReservaInvalida(
                f"Solo se puede confirmar una reserva PENDIENTE (estado actual: {reserva.estado.value})"
            )
        reserva.estado = EstadoReserva.CONFIRMADA
        return self._repo.actualizar(reserva)

    def cancelar_reserva(self, reserva_id: int) -> Reserva:
        reserva = self._obtener(reserva_id)
        if reserva.estado not in (EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA):
            raise ReservaInvalida(
                f"Solo se puede cancelar una reserva PENDIENTE o CONFIRMADA (estado actual: {reserva.estado.value})"
            )
        if reserva.fecha_inicio - self._ahora() <= self.ANTICIPACION_CANCELACION:
            raise ReservaInvalida("Solo se puede cancelar con más de 2 horas de anticipación")
        reserva.estado = EstadoReserva.CANCELADA
        return self._repo.actualizar(reserva)

    def completar_reserva(self, reserva_id: int) -> Reserva:
        reserva = self._obtener(reserva_id)
        if reserva.estado is not EstadoReserva.CONFIRMADA:
            raise ReservaInvalida(
                f"Solo se puede completar una reserva CONFIRMADA (estado actual: {reserva.estado.value})"
            )
        reserva.estado = EstadoReserva.COMPLETADA
        return self._repo.actualizar(reserva)

    # ------------------------------------------------------------- consultas
    def obtener_reserva(self, reserva_id: int) -> Reserva:
        return self._obtener(reserva_id)

    def listar_reservas(
        self,
        cancha_id: int | None = None,
        cliente_id: int | None = None,
        fecha: date | None = None,
        estado: EstadoReserva | str | None = None,
    ) -> list[Reserva]:
        if isinstance(estado, str):
            try:
                estado = EstadoReserva(estado.strip().upper())
            except ValueError:
                validos = ", ".join(e.value for e in EstadoReserva)
                raise ReservaInvalida(f"Estado inválido '{estado}'. Valores permitidos: {validos}")
        return self._repo.listar(
            cancha_id=cancha_id, cliente_id=cliente_id, fecha=fecha, estado=estado
        )

    def consultar_disponibilidad(self, cancha_id: int, fecha: date) -> list[Franja]:
        """Franjas libres (inicio, fin) del día, dentro del horario de operación."""
        self._obtener_cancha_activa(cancha_id)
        medianoche = datetime.combine(fecha, datetime.min.time())
        apertura = medianoche + timedelta(hours=self._apertura)
        cierre = medianoche + timedelta(hours=self._cierre)

        cursor = max(apertura, self._ahora())  # lo ya pasado no está disponible
        ocupadas = sorted(
            self._repo.buscar_cruces(cancha_id, apertura, cierre),
            key=lambda r: r.fecha_inicio,
        )
        libres: list[Franja] = []
        for r in ocupadas:
            if cursor < r.fecha_inicio and cursor < cierre:
                libres.append((cursor, min(r.fecha_inicio, cierre)))
            cursor = max(cursor, r.fecha_fin)
        if cursor < cierre:
            libres.append((cursor, cierre))
        return libres

    # --------------------------------------------------------------- privados
    def _obtener(self, reserva_id: int) -> Reserva:
        reserva = self._repo.obtener_por_id(reserva_id)
        if reserva is None:
            raise ReservaNoEncontrada(f"La reserva {reserva_id} no existe")
        return reserva

    def _obtener_cancha_activa(self, cancha_id: int) -> Cancha:
        cancha = self._repo.obtener_cancha(cancha_id)
        if cancha is None:
            raise CanchaNoEncontrada(f"La cancha {cancha_id} no existe")
        if not cancha.activa:
            raise CanchaNoDisponible(f"La cancha {cancha_id} no está activa")
        return cancha
