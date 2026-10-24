"""Adaptador de entrada: API REST (Blueprint Flask) que traduce HTTP <-> servicio."""
from datetime import date, datetime

from flask import Blueprint, current_app, g, jsonify, request, url_for

from flaskr.application.ports.reservaUseCases import ReservaUseCases
from flaskr.domain.models.reserva import (
    CanchaNoDisponible,
    Reserva,
    ReservaInvalida,
    ReservaNoEncontrada,
)

reservas_bp = Blueprint("reservas", __name__)


# ------------------------------------------------------------ composición
def _servicio() -> ReservaUseCases:
    """Obtiene el caso de uso configurado por el punto de composición."""
    factory = current_app.extensions["reserva_service_factory"]
    if "servicio" not in g:
        g.servicio = factory()
    return g.servicio


# ------------------------------------------------- errores de dominio -> HTTP
def _error(codigo: int, exc: Exception):
    return jsonify({"error": str(exc)}), codigo


@reservas_bp.errorhandler(ReservaInvalida)
def _invalida(exc):
    return _error(400, exc)


@reservas_bp.errorhandler(ReservaNoEncontrada)
def _no_encontrada(exc):
    return _error(404, exc)


@reservas_bp.errorhandler(CanchaNoDisponible)
def _no_disponible(exc):
    return _error(409, exc)


# ----------------------------------------------------- parseo y validación
def _entero(valor, nombre: str) -> int:
    try:
        if valor is None or isinstance(valor, (bool, float)):
            raise ValueError
        return int(str(valor).strip())
    except ValueError:
        raise ReservaInvalida(f"'{nombre}' debe ser un número entero")


def _fecha_hora(valor, nombre: str) -> datetime:
    if not isinstance(valor, str):
        raise ReservaInvalida(f"'{nombre}' es obligatorio (ISO 8601, ej. 2030-01-16T10:00:00)")
    try:
        dt = datetime.fromisoformat(valor)
    except ValueError:
        raise ReservaInvalida(f"'{nombre}' no tiene formato ISO 8601 válido: {valor!r}")
    return dt.astimezone().replace(tzinfo=None) if dt.tzinfo else dt


def _fecha(valor, nombre: str = "fecha") -> date:
    if not valor:
        raise ReservaInvalida(f"El parámetro '{nombre}' es obligatorio (YYYY-MM-DD)")
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ReservaInvalida(f"'{nombre}' debe tener formato YYYY-MM-DD: {valor!r}")


def _cuerpo_json() -> dict:
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ReservaInvalida("El cuerpo de la petición debe ser un objeto JSON")
    return datos


def _reserva_json(r: Reserva) -> dict:
    return {
        "id": r.id,
        "cancha_id": r.cancha_id,
        "cliente_id": r.cliente_id,
        "fecha_inicio": r.fecha_inicio.isoformat(),
        "fecha_fin": r.fecha_fin.isoformat(),
        "estado": r.estado.value,
        "total": r.total,
    }


# --------------------------------------------------------------- endpoints
@reservas_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@reservas_bp.get("/api/canchas")
def listar_canchas():
    canchas = _servicio().listar_canchas()
    return jsonify(
        [
            {
                "id": cancha.id,
                "nombre": cancha.nombre,
                "deporte": cancha.deporte.value,
                "precio_hora": cancha.precio_hora,
            }
            for cancha in canchas
        ]
    )


@reservas_bp.get("/api/clientes")
def buscar_clientes():
    texto = request.args.get("q", "")
    clientes = _servicio().buscar_cliente(texto)
    return jsonify(
        [
            {
                "id": cliente.id,
                "nombre": cliente.nombre,
                "documento": cliente.documento,
            }
            for cliente in clientes
        ]
    )


@reservas_bp.post("/api/reservas")
def crear_reserva():
    datos = _cuerpo_json()
    faltan = [c for c in ("cancha_id", "cliente_id", "fecha_inicio", "fecha_fin") if c not in datos]
    if faltan:
        raise ReservaInvalida(f"Faltan campos obligatorios: {', '.join(faltan)}")
    reserva = _servicio().crear_reserva(
        _entero(datos["cancha_id"], "cancha_id"),
        _entero(datos["cliente_id"], "cliente_id"),
        _fecha_hora(datos["fecha_inicio"], "fecha_inicio"),
        _fecha_hora(datos["fecha_fin"], "fecha_fin"),
    )
    respuesta = jsonify(_reserva_json(reserva))
    respuesta.status_code = 201
    respuesta.headers["Location"] = url_for("reservas.obtener_reserva", reserva_id=reserva.id)
    return respuesta


@reservas_bp.get("/api/reservas")
def listar_reservas():
    args = request.args
    reservas = _servicio().listar_reservas(
        cancha_id=_entero(args["cancha_id"], "cancha_id") if args.get("cancha_id") else None,
        cliente_id=_entero(args["cliente_id"], "cliente_id") if args.get("cliente_id") else None,
        fecha=_fecha(args["fecha"]) if args.get("fecha") else None,
        estado=args.get("estado") or None,
    )
    return jsonify([_reserva_json(r) for r in reservas])


@reservas_bp.get("/api/reservas/<int:reserva_id>")
def obtener_reserva(reserva_id: int):
    return jsonify(_reserva_json(_servicio().obtener_reserva(reserva_id)))


@reservas_bp.patch("/api/reservas/<int:reserva_id>/confirmar")
def confirmar_reserva(reserva_id: int):
    return jsonify(_reserva_json(_servicio().confirmar_reserva(reserva_id)))


@reservas_bp.patch("/api/reservas/<int:reserva_id>/cancelar")
def cancelar_reserva(reserva_id: int):
    return jsonify(_reserva_json(_servicio().cancelar_reserva(reserva_id)))


@reservas_bp.patch("/api/reservas/<int:reserva_id>/completar")
def completar_reserva(reserva_id: int):
    return jsonify(_reserva_json(_servicio().completar_reserva(reserva_id)))


@reservas_bp.get("/api/canchas/<int:cancha_id>/disponibilidad")
def disponibilidad(cancha_id: int):
    fecha = _fecha(request.args.get("fecha"))
    franjas = _servicio().consultar_disponibilidad(cancha_id, fecha)
    return jsonify(
        {
            "cancha_id": cancha_id,
            "fecha": fecha.isoformat(),
            "franjas_libres": [{"inicio": i.isoformat(), "fin": f.isoformat()} for i, f in franjas],
        }
    )
