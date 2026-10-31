"""Adaptador MCP para descubrir y gestionar reservas de canchas."""
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date, datetime
from typing import ContextManager, TypeVar
from typing_extensions import TypedDict

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from flaskr.application.ports.reservaUseCases import ReservaUseCases
from flaskr.domain.models.cancha import Deporte
from flaskr.domain.models.reserva import (
    CanchaNoDisponible,
    EstadoReserva,
    Reserva,
    ReservaInvalida,
    ReservaNoEncontrada,
)


class Horario(TypedDict):
    inicio: str
    fin: str


class CanchaResult(TypedDict):
    id: int | None
    nombre: str
    deporte: str
    precio_hora: float


class ClienteResult(TypedDict):
    id: int | None
    nombre: str


class ReservaResult(TypedDict):
    id: int | None
    cancha_id: int
    cliente_id: int
    fecha_inicio: str
    fecha_fin: str
    estado: str
    total: float


class CotizacionResult(TypedDict):
    cancha_id: int
    fecha_inicio: str
    fecha_fin: str
    duracion_minutos: int
    precio_hora: float
    total: float


ServiceScopeFactory = Callable[[], ContextManager[ReservaUseCases]]
Result = TypeVar("Result")


def _reserva_dict(reserva: Reserva) -> ReservaResult:
    return {
        "id": reserva.id,
        "cancha_id": reserva.cancha_id,
        "cliente_id": reserva.cliente_id,
        "fecha_inicio": reserva.fecha_inicio.isoformat(),
        "fecha_fin": reserva.fecha_fin.isoformat(),
        "estado": reserva.estado.value,
        "total": reserva.total,
    }


def crear_servidor_mcp(proveedor_servicio: ServiceScopeFactory) -> FastMCP:
    """Construye el servidor usando casos de uso suministrados por composición."""
    mcp = FastMCP("reservas-canchas")

    def ejecutar(operacion: Callable[[ReservaUseCases], Result]) -> Result:
        try:
            with proveedor_servicio() as servicio:
                return operacion(servicio)
        except (ReservaInvalida, ReservaNoEncontrada, CanchaNoDisponible) as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(annotations={"readOnlyHint": True})
    def listar_canchas(deporte: Deporte | None = None) -> list[CanchaResult]:
        """Lista canchas activas, opcionalmente filtradas por deporte."""
        canchas = ejecutar(lambda servicio: servicio.listar_canchas(deporte))
        return [
            {
                "id": cancha.id,
                "nombre": cancha.nombre,
                "deporte": cancha.deporte.value,
                "precio_hora": cancha.precio_hora,
            }
            for cancha in canchas
        ]

    @mcp.tool(annotations={"readOnlyHint": True})
    def buscar_cliente(texto: str) -> list[ClienteResult]:
        """Busca un cliente por nombre o documento y devuelve solo id y nombre."""
        clientes = ejecutar(lambda servicio: servicio.buscar_cliente(texto))
        return [{"id": cliente.id, "nombre": cliente.nombre} for cliente in clientes]

    @mcp.tool(annotations={"readOnlyHint": True})
    def consultar_disponibilidad(cancha_id: int, fecha: date) -> list[Horario]:
        """Consulta franjas libres de 08:00 a 22:00 para una cancha y fecha."""
        franjas = ejecutar(
            lambda servicio: servicio.consultar_disponibilidad(cancha_id, fecha)
        )
        return [{"inicio": inicio.isoformat(), "fin": fin.isoformat()} for inicio, fin in franjas]

    @mcp.tool(annotations={"readOnlyHint": True})
    def sugerir_horarios(
        cancha_id: int, fecha: date, duracion_horas: float
    ) -> list[Horario]:
        """Sugiere hasta 10 horarios libres, con inicios cada 30 minutos."""
        franjas = ejecutar(
            lambda servicio: servicio.sugerir_horarios(cancha_id, fecha, duracion_horas)
        )
        return [{"inicio": inicio.isoformat(), "fin": fin.isoformat()} for inicio, fin in franjas]

    @mcp.tool(annotations={"readOnlyHint": True})
    def cotizar_reserva(
        cancha_id: int, inicio: datetime, fin: datetime
    ) -> CotizacionResult:
        """Valida disponibilidad y calcula el precio, sin crear la reserva."""
        cotizacion = ejecutar(
            lambda servicio: servicio.cotizar_reserva(cancha_id, inicio, fin)
        )
        return {
            "cancha_id": cotizacion.cancha_id,
            "fecha_inicio": cotizacion.fecha_inicio.isoformat(),
            "fecha_fin": cotizacion.fecha_fin.isoformat(),
            "duracion_minutos": int(cotizacion.duracion.total_seconds() // 60),
            "precio_hora": cotizacion.precio_hora,
            "total": cotizacion.total,
        }

    @mcp.tool(annotations={"readOnlyHint": True})
    def listar_reservas(
        cancha_id: int | None = None,
        cliente_id: int | None = None,
        fecha: date | None = None,
        estado: EstadoReserva | None = None,
    ) -> list[ReservaResult]:
        """Lista reservas filtrando opcionalmente por cancha, cliente, fecha y estado."""
        reservas = ejecutar(
            lambda servicio: servicio.listar_reservas(
                cancha_id=cancha_id,
                cliente_id=cliente_id,
                fecha=fecha,
                estado=estado,
            )
        )
        return [_reserva_dict(reserva) for reserva in reservas]

    @mcp.tool(annotations={"readOnlyHint": True})
    def obtener_reserva(reserva_id: int) -> dict[str, object]:
        """Devuelve el detalle de una reserva."""
        reserva = ejecutar(lambda servicio: servicio.obtener_reserva(reserva_id))
        return _reserva_dict(reserva)

    @mcp.tool
    def crear_reserva(
        cancha_id: int, cliente_id: int, inicio: datetime, fin: datetime
    ) -> dict[str, object]:
        """Crea una reserva pendiente; confirma con el usuario antes de ejecutar."""
        reserva = ejecutar(
            lambda servicio: servicio.crear_reserva(cancha_id, cliente_id, inicio, fin)
        )
        return _reserva_dict(reserva)

    @mcp.tool(annotations={"destructiveHint": True})
    def cancelar_reserva(reserva_id: int) -> dict[str, object]:
        """Cancela una reserva pendiente o confirmada; requiere autorización del usuario."""
        reserva = ejecutar(lambda servicio: servicio.cancelar_reserva(reserva_id))
        return _reserva_dict(reserva)

    @mcp.tool
    def confirmar_reserva(reserva_id: int) -> dict[str, object]:
        """Confirma una reserva pendiente."""
        reserva = ejecutar(lambda servicio: servicio.confirmar_reserva(reserva_id))
        return _reserva_dict(reserva)

    @mcp.tool
    def completar_reserva(reserva_id: int) -> dict[str, object]:
        """Marca como completada una reserva confirmada."""
        reserva = ejecutar(lambda servicio: servicio.completar_reserva(reserva_id))
        return _reserva_dict(reserva)

    @mcp.resource("canchas://catalogo")
    def catalogo_canchas() -> str:
        """Catálogo de canchas activas, en formato JSON."""
        return json.dumps(listar_canchas(), ensure_ascii=False)

    @mcp.resource("reservas://{reserva_id}")
    def recurso_reserva(reserva_id: int) -> str:
        """Detalle de una reserva en formato JSON."""
        return json.dumps(obtener_reserva(reserva_id), ensure_ascii=False)

    @mcp.prompt
    def agendar_cancha(deporte: Deporte, fecha: date) -> str:
        """Guía al asistente para buscar, cotizar y solicitar una reserva."""
        return (
            f"Ayuda a agendar una cancha de {deporte.value} para el {fecha.isoformat()}. "
            "Primero lista las canchas y consulta disponibilidad o sugiere horarios. "
            "Busca al cliente y confirma su identidad usando solo la información necesaria. "
            "Cotiza el horario elegido. Antes de crear la reserva, muestra cancha, fecha, "
            "horario y precio y solicita confirmación explícita. No llames crear_reserva "
            "hasta que el usuario confirme."
        )

    return mcp


def _crear_proveedor_servicio(
    database_url: str, hora_apertura: int, hora_cierre: int
) -> tuple[ServiceScopeFactory, Callable[[], None]]:
    from flaskr.domain.services.reservaService import ReservaService
    from flaskr.infrastructure.adaptadorSalida.reservaRepositorySQL import ReservaRepositorySQL
    from flaskr.infrastructure.db.session import crear_session_factory
    from flaskr.infrastructure.db.engine import crear_engine
    from flaskr.inicializarBD import crear_tablas

    engine = crear_engine(database_url)
    crear_tablas(engine)
    session_factory = crear_session_factory(engine)

    @contextmanager
    def proveedor() -> Iterator[ReservaUseCases]:
        with session_factory() as session:
            yield ReservaService(
                ReservaRepositorySQL(session),
                hora_apertura=hora_apertura,
                hora_cierre=hora_cierre,
            )

    return proveedor, engine.dispose


def main() -> None:
    from dotenv import load_dotenv

    from flaskr.configuracion import obtener_config

    load_dotenv()
    config = obtener_config()
    proveedor, cerrar_engine = _crear_proveedor_servicio(
        config.DATABASE_URL,
        config.HORA_APERTURA,
        config.HORA_CIERRE,
    )
    try:
        crear_servidor_mcp(proveedor).run()
    finally:
        cerrar_engine()


if __name__ == "__main__":
    main()
