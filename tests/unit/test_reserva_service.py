from datetime import date, datetime, timedelta

import pytest

from flaskr.domain.models.reserva import (
    CanchaNoDisponible,
    CanchaNoEncontrada,
    ClienteNoEncontrado,
    EstadoReserva,
    Reserva,
    ReservaInvalida,
    ReservaNoEncontrada,
)

DIA = datetime(2030, 1, 16)  # el día siguiente a "ahora"


def h(hora, minuto=0, dia=DIA):
    return dia.replace(hour=hora, minute=minuto)


# ------------------------------------------------------------------ crear
def test_crear_calcula_total_y_queda_pendiente(servicio):
    r = servicio.crear_reserva(1, 1, h(10), h(12))
    assert r.id == 1
    assert r.estado is EstadoReserva.PENDIENTE
    assert r.total == 200.0


def test_total_con_fracciones_de_hora(servicio):
    assert servicio.crear_reserva(1, 1, h(10), h(11, 30)).total == 150.0


def test_catalogo_y_busqueda_de_clientes(servicio):
    assert [cancha.id for cancha in servicio.listar_canchas("padel")] == [3]
    assert [cliente.nombre for cliente in servicio.buscar_cliente("111")] == ["Ana"]


def test_cotizar_no_crea_reserva(servicio, repo):
    cotizacion = servicio.cotizar_reserva(1, h(10), h(11, 30))
    assert cotizacion.total == 150.0
    assert cotizacion.precio_hora == 100.0
    assert repo.reservas == {}


def test_sugerir_horarios_en_intervalos_de_30_minutos(servicio):
    horarios = servicio.sugerir_horarios(1, DIA.date(), 1)
    assert horarios[:2] == [(h(8), h(9)), (h(8, 30), h(9, 30))]
    assert len(horarios) == 10


def test_sugerir_horarios_rechaza_duracion_infinita(servicio):
    with pytest.raises(ReservaInvalida, match="número"):
        servicio.sugerir_horarios(1, DIA.date(), float("inf"))


def test_duraciones_limite_son_validas(servicio):
    servicio.crear_reserva(1, 1, h(8), h(9))    # exactamente 1 h
    servicio.crear_reserva(1, 1, h(10), h(13))  # exactamente 3 h


@pytest.mark.parametrize(
    "inicio,fin",
    [(h(12), h(10)), (h(10), h(10)), (h(10), h(10, 59)), (h(10), h(13, 1))],
    ids=["fin_antes", "duracion_cero", "menos_de_1h", "mas_de_3h"],
)
def test_duracion_invalida(servicio, inicio, fin):
    with pytest.raises(ReservaInvalida):
        servicio.crear_reserva(1, 1, inicio, fin)


def test_no_permite_reservas_en_el_pasado(servicio, ahora):
    with pytest.raises(ReservaInvalida, match="pasado"):
        servicio.crear_reserva(1, 1, ahora - timedelta(hours=3), ahora - timedelta(hours=1))


def test_cancha_inexistente(servicio):
    with pytest.raises(CanchaNoEncontrada):
        servicio.crear_reserva(99, 1, h(10), h(11))


def test_cancha_inactiva(servicio):
    with pytest.raises(CanchaNoDisponible):
        servicio.crear_reserva(2, 1, h(10), h(11))


def test_cliente_inexistente(servicio):
    with pytest.raises(ClienteNoEncontrado):
        servicio.crear_reserva(1, 99, h(10), h(11))


@pytest.mark.parametrize(
    "inicio,fin",
    [(h(10), h(12)), (h(9), h(11)), (h(11), h(13)), (h(10, 30), h(11, 30)), (h(9), h(12))],
    ids=["identica", "solape_inicio", "solape_fin", "contenida", "contiene"],
)
def test_cruce_de_horario(servicio, inicio, fin):
    servicio.crear_reserva(1, 1, h(10), h(12))
    with pytest.raises(CanchaNoDisponible):
        servicio.crear_reserva(1, 2, inicio, fin)


def test_reservas_contiguas_o_en_otra_cancha_no_cruzan(servicio):
    servicio.crear_reserva(1, 1, h(10), h(12))
    servicio.crear_reserva(1, 2, h(12), h(14))  # justo después
    servicio.crear_reserva(1, 2, h(8), h(10))   # justo antes
    servicio.crear_reserva(3, 2, h(10), h(12))  # misma hora, otra cancha


def test_reserva_cancelada_libera_el_horario(servicio):
    r = servicio.crear_reserva(1, 1, h(10), h(12))
    servicio.cancelar_reserva(r.id)
    assert servicio.crear_reserva(1, 2, h(10), h(12)).id != r.id


# --------------------------------------------------------- cambios de estado
def test_confirmar_y_completar(servicio):
    r = servicio.crear_reserva(1, 1, h(10), h(12))
    assert servicio.confirmar_reserva(r.id).estado is EstadoReserva.CONFIRMADA
    assert servicio.completar_reserva(r.id).estado is EstadoReserva.COMPLETADA


def test_confirmar_solo_pendientes(servicio):
    r = servicio.crear_reserva(1, 1, h(10), h(12))
    servicio.confirmar_reserva(r.id)
    with pytest.raises(ReservaInvalida):
        servicio.confirmar_reserva(r.id)


def test_completar_solo_confirmadas(servicio):
    r = servicio.crear_reserva(1, 1, h(10), h(12))
    with pytest.raises(ReservaInvalida):
        servicio.completar_reserva(r.id)


@pytest.mark.parametrize("confirmar", [False, True])
def test_cancelar_pendiente_o_confirmada(servicio, confirmar):
    r = servicio.crear_reserva(1, 1, h(10), h(12))
    if confirmar:
        servicio.confirmar_reserva(r.id)
    assert servicio.cancelar_reserva(r.id).estado is EstadoReserva.CANCELADA


@pytest.mark.parametrize("anticipacion", [timedelta(hours=1), timedelta(hours=2)])
def test_cancelacion_tardia(servicio, ahora, anticipacion):
    inicio = ahora + anticipacion  # faltan 2 h o menos
    r = servicio.crear_reserva(1, 1, inicio, inicio + timedelta(hours=1))
    with pytest.raises(ReservaInvalida, match="2 horas"):
        servicio.cancelar_reserva(r.id)


def test_cancelar_con_mas_de_2_horas(servicio, ahora):
    inicio = ahora + timedelta(hours=2, minutes=1)
    r = servicio.crear_reserva(1, 1, inicio, inicio + timedelta(hours=1))
    assert servicio.cancelar_reserva(r.id).estado is EstadoReserva.CANCELADA


def test_no_se_puede_cancelar_cancelada_ni_completada(servicio):
    a = servicio.crear_reserva(1, 1, h(10), h(11))
    servicio.cancelar_reserva(a.id)
    b = servicio.crear_reserva(1, 1, h(12), h(13))
    servicio.confirmar_reserva(b.id)
    servicio.completar_reserva(b.id)
    for r in (a, b):
        with pytest.raises(ReservaInvalida):
            servicio.cancelar_reserva(r.id)


@pytest.mark.parametrize("metodo", ["confirmar_reserva", "cancelar_reserva", "completar_reserva", "obtener_reserva"])
def test_reserva_inexistente(servicio, metodo):
    with pytest.raises(ReservaNoEncontrada):
        getattr(servicio, metodo)(999)


# ----------------------------------------------------------------- listar
@pytest.fixture
def con_datos(servicio):
    a = servicio.crear_reserva(1, 1, h(10), h(11))
    servicio.crear_reserva(1, 2, h(12), h(13))
    servicio.crear_reserva(3, 1, h(10, dia=DIA + timedelta(days=1)), h(12, dia=DIA + timedelta(days=1)))
    servicio.confirmar_reserva(a.id)
    return servicio


def test_listar_sin_filtros(con_datos):
    assert len(con_datos.listar_reservas()) == 3


@pytest.mark.parametrize(
    "filtros,esperadas",
    [
        ({"cancha_id": 1}, 2),
        ({"cliente_id": 1}, 2),
        ({"fecha": date(2030, 1, 16)}, 2),
        ({"fecha": date(2030, 1, 17)}, 1),
        ({"fecha": date(2030, 1, 20)}, 0),
        ({"estado": "confirmada"}, 1),
        ({"estado": EstadoReserva.PENDIENTE}, 2),
        ({"cancha_id": 1, "cliente_id": 2, "estado": "PENDIENTE"}, 1),
    ],
)
def test_listar_con_filtros(con_datos, filtros, esperadas):
    assert len(con_datos.listar_reservas(**filtros)) == esperadas


def test_listar_estado_invalido(servicio):
    with pytest.raises(ReservaInvalida, match="Estado inválido"):
        servicio.listar_reservas(estado="NOEXISTE")


# ----------------------------------------------------------- disponibilidad
def test_disponibilidad_dia_libre(servicio):
    assert servicio.consultar_disponibilidad(1, DIA.date()) == [(h(8), h(22))]


def test_disponibilidad_con_reservas(servicio):
    servicio.crear_reserva(1, 1, h(10), h(12))
    servicio.crear_reserva(1, 1, h(12), h(13))  # contigua
    servicio.crear_reserva(1, 1, h(20), h(22))  # al cierre
    assert servicio.consultar_disponibilidad(1, DIA.date()) == [
        (h(8), h(10)),
        (h(13), h(20)),
    ]


def test_disponibilidad_ignora_otras_canchas_y_canceladas(servicio):
    servicio.crear_reserva(3, 1, h(10), h(12))
    r = servicio.crear_reserva(1, 1, h(14), h(16))
    servicio.cancelar_reserva(r.id)
    assert servicio.consultar_disponibilidad(1, DIA.date()) == [(h(8), h(22))]


def test_disponibilidad_hoy_excluye_lo_ya_pasado(servicio, repo, reloj, ahora):
    hoy = ahora.date()
    assert servicio.consultar_disponibilidad(1, hoy) == [(ahora, h(22, dia=ahora))]
    # reserva en curso (08:00-10:00) cuando son las 09:00
    repo.guardar(Reserva(cancha_id=1, cliente_id=1, fecha_inicio=h(8, dia=ahora), fecha_fin=h(10, dia=ahora)))
    assert servicio.consultar_disponibilidad(1, hoy) == [(h(10, dia=ahora), h(22, dia=ahora))]
    reloj.ahora = h(23, dia=ahora)
    assert servicio.consultar_disponibilidad(1, hoy) == []


def test_disponibilidad_fecha_pasada_vacia(servicio):
    assert servicio.consultar_disponibilidad(1, date(2030, 1, 1)) == []


def test_disponibilidad_cancha_inexistente_o_inactiva(servicio):
    with pytest.raises(CanchaNoEncontrada):
        servicio.consultar_disponibilidad(99, DIA.date())
    with pytest.raises(CanchaNoDisponible):
        servicio.consultar_disponibilidad(2, DIA.date())
