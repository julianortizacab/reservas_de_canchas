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
    # Arrange
    cancha_id, cliente_id = 1, 1

    # Act
    r = servicio.crear_reserva(cancha_id, cliente_id, h(10), h(12))

    # Assert
    assert r.id == 1
    assert r.estado is EstadoReserva.PENDIENTE
    assert r.total == 200.0


def test_total_con_fracciones_de_hora(servicio):
    # Arrange
    inicio, fin = h(10), h(11, 30)

    # Act
    reserva = servicio.crear_reserva(1, 1, inicio, fin)

    # Assert
    assert reserva.total == 150.0


def test_catalogo_y_busqueda_de_clientes(servicio):
    # Arrange
    deporte, texto = "padel", "111"

    # Act
    canchas = servicio.listar_canchas(deporte)
    clientes = servicio.buscar_cliente(texto)

    # Assert
    assert [cancha.id for cancha in canchas] == [3]
    assert [cliente.nombre for cliente in clientes] == ["Ana"]


def test_listar_canchas_rechaza_deporte_invalido(servicio):
    # Arrange
    deporte = "golf"

    # Act
    with pytest.raises(ReservaInvalida, match="Deporte inválido") as error:
        servicio.listar_canchas(deporte)

    # Assert
    assert error.type is ReservaInvalida


@pytest.mark.parametrize("texto", ["", "   "], ids=["vacio", "solo_espacios"])
def test_buscar_cliente_rechaza_texto_vacio(servicio, texto):
    # Arrange
    termino = texto

    # Act
    with pytest.raises(ReservaInvalida, match="no puede estar vacío") as error:
        servicio.buscar_cliente(termino)

    # Assert
    assert error.type is ReservaInvalida


def test_cotizar_no_crea_reserva(servicio, repo):
    # Arrange
    inicio, fin = h(10), h(11, 30)

    # Act
    cotizacion = servicio.cotizar_reserva(1, inicio, fin)

    # Assert
    assert cotizacion.total == 150.0
    assert cotizacion.precio_hora == 100.0
    assert repo.reservas == {}


def test_cotizar_rechaza_horario_ocupado_sin_crear_reserva(servicio, repo):
    # Arrange
    servicio.crear_reserva(1, 1, h(10), h(11))
    reservas_existentes = dict(repo.reservas)

    # Act
    with pytest.raises(CanchaNoDisponible) as error:
        servicio.cotizar_reserva(1, h(10), h(11))

    # Assert
    assert error.type is CanchaNoDisponible
    assert repo.reservas == reservas_existentes


@pytest.mark.parametrize(
    "inicio,fin",
    [
        (h(10), h(10, 30)),
        (h(10), h(13, 1)),
        (datetime(2030, 1, 15, 8), datetime(2030, 1, 15, 10)),
    ],
    ids=["menos_de_una_hora", "mas_de_tres_horas", "fecha_pasada"],
)
def test_cotizar_rechaza_datos_invalidos(servicio, inicio, fin):
    # Arrange
    cancha_id = 1

    # Act
    with pytest.raises(ReservaInvalida) as error:
        servicio.cotizar_reserva(cancha_id, inicio, fin)

    # Assert
    assert error.type is ReservaInvalida


def test_sugerir_horarios_en_intervalos_de_30_minutos(servicio):
    # Arrange
    fecha, duracion_horas = DIA.date(), 1

    # Act
    horarios = servicio.sugerir_horarios(1, fecha, duracion_horas)

    # Assert
    assert horarios[:2] == [(h(8), h(9)), (h(8, 30), h(9, 30))]
    assert len(horarios) == 10


def test_sugerir_horarios_excluye_franjas_ocupadas(servicio):
    # Arrange
    fecha, duracion_horas = DIA.date(), 1
    servicio.crear_reserva(1, 1, h(8), h(10))

    # Act
    horarios = servicio.sugerir_horarios(1, fecha, duracion_horas)

    # Assert
    assert horarios
    assert all(inicio >= h(10) for inicio, _ in horarios)


@pytest.mark.parametrize(
    "duracion",
    [0, 0.5, 3.5, float("inf"), float("nan")],
    ids=["cero", "menor_al_minimo", "mayor_al_maximo", "infinita", "no_numero"],
)
def test_sugerir_horarios_rechaza_duraciones_invalidas(servicio, duracion):
    # Arrange
    fecha = DIA.date()

    # Act
    with pytest.raises(ReservaInvalida) as error:
        servicio.sugerir_horarios(1, fecha, duracion)

    # Assert
    assert error.type is ReservaInvalida


def test_duraciones_limite_son_validas(servicio):
    # Arrange
    horarios = [(h(8), h(9)), (h(10), h(13))]

    # Act
    reservas = [
        servicio.crear_reserva(1, 1, inicio, fin)
        for inicio, fin in horarios
    ]

    # Assert
    assert len(servicio.listar_reservas()) == len(reservas)


@pytest.mark.parametrize(
    "inicio,fin",
    [(h(12), h(10)), (h(10), h(10)), (h(10), h(10, 59)), (h(10), h(13, 1))],
    ids=["fin_antes", "duracion_cero", "menos_de_1h", "mas_de_3h"],
)
def test_duracion_invalida(servicio, inicio, fin):
    # Arrange
    cancha_id, cliente_id = 1, 1

    # Act
    with pytest.raises(ReservaInvalida) as error:
        servicio.crear_reserva(cancha_id, cliente_id, inicio, fin)

    # Assert
    assert error.type is ReservaInvalida


def test_no_permite_reservas_en_el_pasado(servicio, ahora):
    # Arrange
    inicio, fin = ahora - timedelta(hours=3), ahora - timedelta(hours=1)

    # Act
    with pytest.raises(ReservaInvalida, match="pasado") as error:
        servicio.crear_reserva(1, 1, inicio, fin)

    # Assert
    assert error.type is ReservaInvalida


def test_cancha_inexistente(servicio):
    # Arrange
    cancha_id = 99

    # Act
    with pytest.raises(CanchaNoEncontrada) as error:
        servicio.crear_reserva(cancha_id, 1, h(10), h(11))

    # Assert
    assert error.type is CanchaNoEncontrada


def test_cancha_inactiva(servicio):
    # Arrange
    cancha_id = 2

    # Act
    with pytest.raises(CanchaNoDisponible) as error:
        servicio.crear_reserva(cancha_id, 1, h(10), h(11))

    # Assert
    assert error.type is CanchaNoDisponible


def test_cliente_inexistente(servicio):
    # Arrange
    cliente_id = 99

    # Act
    with pytest.raises(ClienteNoEncontrado) as error:
        servicio.crear_reserva(1, cliente_id, h(10), h(11))

    # Assert
    assert error.type is ClienteNoEncontrado


@pytest.mark.parametrize(
    "inicio,fin",
    [(h(10), h(12)), (h(9), h(11)), (h(11), h(13)), (h(10, 30), h(11, 30)), (h(9), h(12))],
    ids=["identica", "solape_inicio", "solape_fin", "contenida", "contiene"],
)
def test_cruce_de_horario(servicio, inicio, fin):
    # Arrange
    servicio.crear_reserva(1, 1, h(10), h(12))

    # Act
    with pytest.raises(CanchaNoDisponible) as error:
        servicio.crear_reserva(1, 2, inicio, fin)

    # Assert
    assert error.type is CanchaNoDisponible


def test_reservas_contiguas_o_en_otra_cancha_no_cruzan(servicio):
    # Arrange
    servicio.crear_reserva(1, 1, h(10), h(12))

    # Act
    servicio.crear_reserva(1, 2, h(12), h(14))  # justo después
    servicio.crear_reserva(1, 2, h(8), h(10))   # justo antes
    servicio.crear_reserva(3, 2, h(10), h(12))  # misma hora, otra cancha

    # Assert
    assert len(servicio.listar_reservas()) == 4


def test_reserva_cancelada_libera_el_horario(servicio):
    # Arrange
    r = servicio.crear_reserva(1, 1, h(10), h(12))

    # Act
    servicio.cancelar_reserva(r.id)
    nueva_reserva = servicio.crear_reserva(1, 2, h(10), h(12))

    # Assert
    assert nueva_reserva.id != r.id


# --------------------------------------------------------- cambios de estado
def test_confirmar_y_completar(servicio):
    # Arrange
    r = servicio.crear_reserva(1, 1, h(10), h(12))

    # Act
    confirmada = servicio.confirmar_reserva(r.id)
    completada = servicio.completar_reserva(r.id)

    # Assert
    assert confirmada.estado is EstadoReserva.CONFIRMADA
    assert completada.estado is EstadoReserva.COMPLETADA


def test_confirmar_solo_pendientes(servicio):
    # Arrange
    r = servicio.crear_reserva(1, 1, h(10), h(12))
    servicio.confirmar_reserva(r.id)

    # Act
    with pytest.raises(ReservaInvalida) as error:
        servicio.confirmar_reserva(r.id)

    # Assert
    assert error.type is ReservaInvalida


def test_completar_solo_confirmadas(servicio):
    # Arrange
    r = servicio.crear_reserva(1, 1, h(10), h(12))

    # Act
    with pytest.raises(ReservaInvalida) as error:
        servicio.completar_reserva(r.id)

    # Assert
    assert error.type is ReservaInvalida


@pytest.mark.parametrize("confirmar", [False, True])
def test_cancelar_pendiente_o_confirmada(servicio, confirmar):
    # Arrange
    r = servicio.crear_reserva(1, 1, h(10), h(12))
    if confirmar:
        servicio.confirmar_reserva(r.id)

    # Act
    cancelada = servicio.cancelar_reserva(r.id)

    # Assert
    assert cancelada.estado is EstadoReserva.CANCELADA


@pytest.mark.parametrize("anticipacion", [timedelta(hours=1), timedelta(hours=2)])
def test_cancelacion_tardia(servicio, ahora, anticipacion):
    # Arrange
    inicio = ahora + anticipacion  # faltan 2 h o menos
    r = servicio.crear_reserva(1, 1, inicio, inicio + timedelta(hours=1))

    # Act
    with pytest.raises(ReservaInvalida, match="2 horas") as error:
        servicio.cancelar_reserva(r.id)

    # Assert
    assert error.type is ReservaInvalida


def test_cancelar_con_mas_de_2_horas(servicio, ahora):
    # Arrange
    inicio = ahora + timedelta(hours=2, minutes=1)
    r = servicio.crear_reserva(1, 1, inicio, inicio + timedelta(hours=1))

    # Act
    cancelada = servicio.cancelar_reserva(r.id)

    # Assert
    assert cancelada.estado is EstadoReserva.CANCELADA


def test_no_se_puede_cancelar_cancelada_ni_completada(servicio):
    # Arrange
    a = servicio.crear_reserva(1, 1, h(10), h(11))
    servicio.cancelar_reserva(a.id)
    b = servicio.crear_reserva(1, 1, h(12), h(13))
    servicio.confirmar_reserva(b.id)
    servicio.completar_reserva(b.id)

    # Act
    for r in (a, b):
        with pytest.raises(ReservaInvalida) as error:
            servicio.cancelar_reserva(r.id)

        # Assert
        assert error.type is ReservaInvalida


@pytest.mark.parametrize("estado_final", [EstadoReserva.CANCELADA, EstadoReserva.COMPLETADA])
def test_confirmar_rechaza_reservas_no_pendientes(servicio, estado_final):
    # Arrange
    reserva = servicio.crear_reserva(1, 1, h(10), h(11))
    if estado_final is EstadoReserva.CANCELADA:
        servicio.cancelar_reserva(reserva.id)
    else:
        servicio.confirmar_reserva(reserva.id)
        servicio.completar_reserva(reserva.id)

    # Act
    with pytest.raises(ReservaInvalida) as error:
        servicio.confirmar_reserva(reserva.id)

    # Assert
    assert error.type is ReservaInvalida


@pytest.mark.parametrize("estado_final", [EstadoReserva.CANCELADA, EstadoReserva.COMPLETADA])
def test_completar_rechaza_reservas_no_confirmadas(servicio, estado_final):
    # Arrange
    reserva = servicio.crear_reserva(1, 1, h(10), h(11))
    if estado_final is EstadoReserva.CANCELADA:
        servicio.cancelar_reserva(reserva.id)
    else:
        servicio.confirmar_reserva(reserva.id)
        servicio.completar_reserva(reserva.id)

    # Act
    with pytest.raises(ReservaInvalida) as error:
        servicio.completar_reserva(reserva.id)

    # Assert
    assert error.type is ReservaInvalida

@pytest.mark.parametrize("metodo", ["confirmar_reserva", "cancelar_reserva", "completar_reserva", "obtener_reserva"])
def test_reserva_inexistente(servicio, metodo):
    # Arrange
    reserva_id = 999

    # Act
    with pytest.raises(ReservaNoEncontrada) as error:
        getattr(servicio, metodo)(reserva_id)

    # Assert
    assert error.type is ReservaNoEncontrada


# ----------------------------------------------------------------- listar
@pytest.fixture
def con_datos(servicio):
    a = servicio.crear_reserva(1, 1, h(10), h(11))
    servicio.crear_reserva(1, 2, h(12), h(13))
    servicio.crear_reserva(3, 1, h(10, dia=DIA + timedelta(days=1)), h(12, dia=DIA + timedelta(days=1)))
    servicio.confirmar_reserva(a.id)
    return servicio


def test_listar_sin_filtros(con_datos):
    # Arrange
    servicio = con_datos

    # Act
    reservas = servicio.listar_reservas()

    # Assert
    assert len(reservas) == 3


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
    # Arrange
    servicio = con_datos

    # Act
    reservas = servicio.listar_reservas(**filtros)

    # Assert
    assert len(reservas) == esperadas


def test_listar_estado_invalido(servicio):
    # Arrange
    estado = "NOEXISTE"

    # Act
    with pytest.raises(ReservaInvalida, match="Estado inválido") as error:
        servicio.listar_reservas(estado=estado)

    # Assert
    assert error.type is ReservaInvalida


# ----------------------------------------------------------- disponibilidad
def test_disponibilidad_dia_libre(servicio):
    # Arrange
    cancha_id, fecha = 1, DIA.date()

    # Act
    franjas = servicio.consultar_disponibilidad(cancha_id, fecha)

    # Assert
    assert franjas == [(h(8), h(22))]


def test_disponibilidad_con_reservas(servicio):
    # Arrange
    servicio.crear_reserva(1, 1, h(10), h(12))
    servicio.crear_reserva(1, 1, h(12), h(13))  # contigua
    servicio.crear_reserva(1, 1, h(20), h(22))  # al cierre

    # Act
    franjas = servicio.consultar_disponibilidad(1, DIA.date())

    # Assert
    assert franjas == [
        (h(8), h(10)),
        (h(13), h(20)),
    ]


def test_disponibilidad_ignora_otras_canchas_y_canceladas(servicio):
    # Arrange
    servicio.crear_reserva(3, 1, h(10), h(12))
    r = servicio.crear_reserva(1, 1, h(14), h(16))
    servicio.cancelar_reserva(r.id)

    # Act
    franjas = servicio.consultar_disponibilidad(1, DIA.date())

    # Assert
    assert franjas == [(h(8), h(22))]


def test_disponibilidad_hoy_excluye_lo_ya_pasado(servicio, repo, reloj, ahora):
    # Arrange
    hoy = ahora.date()

    # Act
    disponibilidad_inicial = servicio.consultar_disponibilidad(1, hoy)

    # Assert
    assert disponibilidad_inicial == [(ahora, h(22, dia=ahora))]

    # Arrange
    # reserva en curso (08:00-10:00) cuando son las 09:00
    repo.guardar(Reserva(cancha_id=1, cliente_id=1, fecha_inicio=h(8, dia=ahora), fecha_fin=h(10, dia=ahora)))

    # Act
    disponibilidad_con_reserva = servicio.consultar_disponibilidad(1, hoy)

    # Assert
    assert disponibilidad_con_reserva == [(h(10, dia=ahora), h(22, dia=ahora))]

    # Arrange
    reloj.ahora = h(23, dia=ahora)

    # Act
    disponibilidad_despues_del_cierre = servicio.consultar_disponibilidad(1, hoy)

    # Assert
    assert disponibilidad_despues_del_cierre == []


def test_disponibilidad_fecha_pasada_vacia(servicio):
    # Arrange
    fecha = date(2030, 1, 1)

    # Act
    franjas = servicio.consultar_disponibilidad(1, fecha)

    # Assert
    assert franjas == []


def test_disponibilidad_ordenada_y_limitada_por_apertura_y_cierre(servicio, repo):
    # Arrange
    repo.guardar(Reserva(
        cancha_id=1,
        cliente_id=1,
        fecha_inicio=h(15),
        fecha_fin=h(17),
    ))
    repo.guardar(Reserva(
        cancha_id=1,
        cliente_id=1,
        fecha_inicio=h(8),
        fecha_fin=h(10),
    ))
    repo.guardar(Reserva(
        cancha_id=1,
        cliente_id=1,
        fecha_inicio=h(20),
        fecha_fin=h(22),
    ))

    # Act
    franjas = servicio.consultar_disponibilidad(1, DIA.date())

    # Assert
    assert franjas == [(h(10), h(15)), (h(17), h(20))]


def test_disponibilidad_cancha_inexistente_o_inactiva(servicio):
    # Arrange
    fecha = DIA.date()

    # Act
    with pytest.raises(CanchaNoEncontrada) as cancha_inexistente:
        servicio.consultar_disponibilidad(99, fecha)
    with pytest.raises(CanchaNoDisponible) as cancha_inactiva:
        servicio.consultar_disponibilidad(2, fecha)

    # Assert
    assert cancha_inexistente.type is CanchaNoEncontrada
    assert cancha_inactiva.type is CanchaNoDisponible
