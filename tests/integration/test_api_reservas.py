from datetime import date, datetime, timedelta

import pytest

from flaskr.infrastructure.db.models.canchaOrm import CanchaOrm

DIA = datetime.combine(date.today() + timedelta(days=3), datetime.min.time())


def h(hora, minuto=0):
    return DIA.replace(hour=hora, minute=minuto)


def cuerpo(inicio, fin, cancha_id=1, cliente_id=1):
    return {"cancha_id": cancha_id, "cliente_id": cliente_id,
            "fecha_inicio": inicio.isoformat(), "fecha_fin": fin.isoformat()}


def crear(client, inicio=None, fin=None, **kw):
    inicio = inicio or h(10)
    return client.post("/api/reservas", json=cuerpo(inicio, fin or inicio + timedelta(hours=2), **kw))


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.get_json() == {"status": "ok"}


def test_panel_web(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Panel de reservas" in r.get_data(as_text=True)


def test_listar_canchas(client):
    r = client.get("/api/canchas")
    assert r.status_code == 200
    canchas = r.get_json()
    assert len(canchas) == 4
    assert canchas[0]["id"] == 3
    assert {"id", "nombre", "deporte", "precio_hora"} <= canchas[0].keys()


def test_buscar_clientes(client):
    r = client.get("/api/clientes", query_string={"q": "Ana"})
    assert r.status_code == 200
    assert r.get_json() == [{"id": 1, "nombre": "Ana Gómez", "documento": "1010101010"}]


def test_buscar_clientes_sin_texto_400(client):
    r = client.get("/api/clientes")
    assert r.status_code == 400
    assert "error" in r.get_json()


# ------------------------------------------------------------------ crear
def test_crear_reserva(client):
    r = crear(client)
    assert r.status_code == 201
    datos = r.get_json()
    assert datos["id"] == 1 and datos["estado"] == "PENDIENTE"
    assert datos["total"] == 160000.0  # 2 h * 80000
    assert r.headers["Location"].endswith("/api/reservas/1")
    assert client.get(r.headers["Location"]).get_json() == datos


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"cancha_id": 1},
        {"cancha_id": "abc", "cliente_id": 1, "fecha_inicio": "2030-01-01T10:00", "fecha_fin": "2030-01-01T11:00"},
        {"cancha_id": 1.5, "cliente_id": 1, "fecha_inicio": "2030-01-01T10:00", "fecha_fin": "2030-01-01T11:00"},
        {"cancha_id": 1, "cliente_id": 1, "fecha_inicio": "mañana", "fecha_fin": "2030-01-01T11:00"},
        {"cancha_id": 1, "cliente_id": 1, "fecha_inicio": 123, "fecha_fin": "2030-01-01T11:00"},
    ],
    ids=["vacio", "incompleto", "id_texto", "id_decimal", "fecha_mala", "fecha_no_texto"],
)
def test_crear_con_datos_mal_formados_400(client, payload):
    r = client.post("/api/reservas", json=payload)
    assert r.status_code == 400 and "error" in r.get_json()


def test_crear_sin_json_400(client):
    r = client.post("/api/reservas", data="no soy json", content_type="text/plain")
    assert r.status_code == 400


@pytest.mark.parametrize(
    "inicio,fin",
    [(h(12), h(10)), (h(10), h(10, 30)), (h(10), h(14))],
    ids=["fin_antes", "menos_de_1h", "mas_de_3h"],
)
def test_crear_duracion_invalida_400(client, inicio, fin):
    assert crear(client, inicio, fin).status_code == 400


def test_crear_en_el_pasado_400(client):
    ayer = h(10) - timedelta(days=10)
    r = crear(client, ayer, ayer + timedelta(hours=1))
    assert r.status_code == 400 and "pasado" in r.get_json()["error"]


def test_crear_cancha_o_cliente_inexistente_404(client):
    assert crear(client, cancha_id=99).status_code == 404
    assert crear(client, cliente_id=99).status_code == 404


def test_crear_en_cancha_inactiva_409(client, app):
    with app.extensions["session_factory"]() as s:
        s.get(CanchaOrm, 1).activa = False
        s.commit()
    assert crear(client).status_code == 409


def test_crear_con_cruce_409(client):
    assert crear(client, h(10), h(12)).status_code == 201
    r = crear(client, h(11), h(13), cliente_id=2)
    assert r.status_code == 409 and "reservada" in r.get_json()["error"]
    assert crear(client, h(12), h(14), cliente_id=2).status_code == 201  # contigua: ok


# ---------------------------------------------------------- obtener / listar
def test_obtener_inexistente_404(client):
    assert client.get("/api/reservas/999").status_code == 404


def test_ruta_inexistente_y_metodo_no_permitido_devuelven_json(client):
    r = client.get("/api/reservas/abc")
    assert r.status_code == 404 and "error" in r.get_json()
    r = client.delete("/api/reservas")
    assert r.status_code == 405 and "error" in r.get_json()


def test_listar_con_filtros(client):
    crear(client, h(10), h(11), cancha_id=1, cliente_id=1)
    crear(client, h(12), h(13), cancha_id=1, cliente_id=2)
    crear(client, h(10), h(11), cancha_id=4, cliente_id=1)
    client.patch("/api/reservas/1/confirmar")

    def ids(**q):
        r = client.get("/api/reservas", query_string=q)
        assert r.status_code == 200
        return [x["id"] for x in r.get_json()]

    assert ids() == [1, 3, 2]  # orden por fecha de inicio y luego id
    assert sorted(ids(cancha_id=1)) == [1, 2]
    assert sorted(ids(cliente_id=1)) == [1, 3]
    assert sorted(ids(fecha=DIA.date().isoformat())) == [1, 2, 3]
    assert ids(fecha="2000-01-01") == []
    assert ids(estado="confirmada") == [1]
    assert sorted(ids(estado="PENDIENTE", cancha_id=1)) == [2]


@pytest.mark.parametrize("query", [{"estado": "xx"}, {"fecha": "16/01/2030"}, {"cancha_id": "abc"}, {"cliente_id": "x"}])
def test_listar_filtros_invalidos_400(client, query):
    assert client.get("/api/reservas", query_string=query).status_code == 400


# -------------------------------------------------------- cambios de estado
def test_confirmar(client):
    crear(client)
    r = client.patch("/api/reservas/1/confirmar")
    assert r.status_code == 200 and r.get_json()["estado"] == "CONFIRMADA"
    assert client.patch("/api/reservas/1/confirmar").status_code == 400  # ya confirmada
    assert client.patch("/api/reservas/999/confirmar").status_code == 404


def test_cancelar_y_liberar_horario(client):
    crear(client)
    r = client.patch("/api/reservas/1/cancelar")
    assert r.status_code == 200 and r.get_json()["estado"] == "CANCELADA"
    assert client.patch("/api/reservas/1/cancelar").status_code == 400
    assert client.patch("/api/reservas/999/cancelar").status_code == 404
    assert crear(client).status_code == 201  # el horario quedó libre


def test_cancelacion_tardia_400(client):
    inicio = datetime.now() + timedelta(minutes=90)
    assert crear(client, inicio, inicio + timedelta(hours=1)).status_code == 201
    r = client.patch("/api/reservas/1/cancelar")
    assert r.status_code == 400 and "2 horas" in r.get_json()["error"]


def test_completar(client):
    crear(client)
    assert client.patch("/api/reservas/1/completar").status_code == 400  # aún PENDIENTE
    client.patch("/api/reservas/1/confirmar")
    r = client.patch("/api/reservas/1/completar")
    assert r.status_code == 200 and r.get_json()["estado"] == "COMPLETADA"
    assert client.patch("/api/reservas/999/completar").status_code == 404


# ----------------------------------------------------------- disponibilidad
def test_disponibilidad(client):
    url = "/api/canchas/1/disponibilidad"
    libre = client.get(url, query_string={"fecha": DIA.date().isoformat()}).get_json()
    assert libre["franjas_libres"] == [{"inicio": h(8).isoformat(), "fin": h(22).isoformat()}]
    crear(client, h(10), h(12))
    r = client.get(url, query_string={"fecha": DIA.date().isoformat()}).get_json()
    assert r["cancha_id"] == 1 and r["fecha"] == DIA.date().isoformat()
    assert r["franjas_libres"] == [
        {"inicio": h(8).isoformat(), "fin": h(10).isoformat()},
        {"inicio": h(12).isoformat(), "fin": h(22).isoformat()},
    ]


def test_disponibilidad_errores(client, app):
    fecha = {"fecha": DIA.date().isoformat()}
    assert client.get("/api/canchas/1/disponibilidad").status_code == 400
    assert client.get("/api/canchas/1/disponibilidad", query_string={"fecha": "hoy"}).status_code == 400
    assert client.get("/api/canchas/99/disponibilidad", query_string=fecha).status_code == 404
    with app.extensions["session_factory"]() as s:
        s.get(CanchaOrm, 2).activa = False
        s.commit()
    assert client.get("/api/canchas/2/disponibilidad", query_string=fecha).status_code == 409


# -------------------------------------------------------------- flujo completo
def test_flujo_completo(client):
    fecha = {"fecha": DIA.date().isoformat()}
    assert crear(client, h(15), h(17)).status_code == 201
    assert client.patch("/api/reservas/1/confirmar").get_json()["estado"] == "CONFIRMADA"
    franjas = client.get("/api/canchas/1/disponibilidad", query_string=fecha).get_json()["franjas_libres"]
    assert [f["fin"] for f in franjas] == [h(15).isoformat(), h(22).isoformat()]
    assert client.patch("/api/reservas/1/cancelar").get_json()["estado"] == "CANCELADA"
    franjas = client.get("/api/canchas/1/disponibilidad", query_string=fecha).get_json()["franjas_libres"]
    assert len(franjas) == 1
