# Reservas de canchas deportivas

API REST en Flask con arquitectura hexagonal (puertos y adaptadores).

```
HTTP/Flask -> Controller -> ReservaUseCases (puerto de entrada)
                                ^
                                | implementado por
                Domain/ReservaService -> ReservaRepository (puerto de salida)
                                                  ^
                                                  | implementado por
                                    ReservaRepositorySQL (SQLAlchemy 2.x)
```
Los modelos, servicios y contratos de repositorio están bajo `flaskr/domain`;
ninguno depende de Flask ni de SQLAlchemy. La fábrica `create_app` es el punto de
composición: conecta los adaptadores concretos y gestiona la sesión por petición.
El controlador solo conoce el puerto de casos de uso; el servicio solo conoce el
contrato de repositorio.

## Instalación (Python 3.11+)
```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # opcional: ajusta la configuración
```

## Ejecución
```bash
python -m flaskr.inicializarBD     # crea tablas y datos semilla (4 canchas, 3 clientes, admin)
flask --app flaskr run             # http://127.0.0.1:5000
```
El panel web de reservas está disponible en `http://127.0.0.1:5000/`.

## Servidor MCP (FastMCP)
El adaptador MCP comparte los casos de uso y reglas de negocio de la API REST.
Arranca un servidor MCP por stdio:
```bash
python -m flaskr.infrastructure.adaptadorEntrada.reservaMcpServer
```

Tools disponibles: `listar_canchas`, `buscar_cliente`,
`consultar_disponibilidad`, `sugerir_horarios`, `cotizar_reserva`,
`listar_reservas`, `obtener_reserva`, `crear_reserva`, `confirmar_reserva`,
`cancelar_reserva` y `completar_reserva`. Las sugerencias empiezan cada 30
minutos y devuelven como máximo 10 opciones. La cotización valida horario y
precio, pero no reserva el espacio; `crear_reserva` vuelve a validar.
Incluye los Resources `canchas://catalogo`, `reservas://{reserva_id}` y el
Prompt `agendar_cancha`. La confirmación humana debe ser gestionada por el
cliente MCP antes de llamar tools de escritura; las anotaciones MCP no son
controles de autorización.

## Tests
```bash
pytest                             # unit + integration
pytest --cov=flaskr --cov-report=term-missing
```

## Configuración (variables de entorno)
| Variable | Por defecto | Uso |
|---|---|---|
| `APP_ENV` | `dev` | `dev` o `test` |
| `DATABASE_URL` | `sqlite:///reservas.db` | URL SQLAlchemy |
| `TEST_DATABASE_URL` | `sqlite:///:memory:` | BD del entorno `test` |
| `ADMIN_PASSWORD` | `admin123` | contraseña del admin sembrado (cámbiala) |
| `HORA_APERTURA` / `HORA_CIERRE` | `8` / `22` | ventana para calcular disponibilidad |

## API
| Método | Ruta | Respuestas |
|---|---|---|
| POST | `/api/reservas` | 201, 400, 404, 409 |
| GET | `/api/reservas?cancha_id=&cliente_id=&fecha=&estado=` | 200, 400 |
| GET | `/api/reservas/<id>` | 200, 404 |
| PATCH | `/api/reservas/<id>/confirmar` · `/cancelar` · `/completar` | 200, 400, 404 |
| GET | `/api/canchas/<id>/disponibilidad?fecha=YYYY-MM-DD` | 200, 400, 404, 409 |
| GET | `/health` | 200 |

Errores: `{"error": "mensaje"}` — 400 `ReservaInvalida`, 404 `ReservaNoEncontrada`, 409 `CanchaNoDisponible`.

Ejemplo:
```bash
curl -X POST localhost:5000/api/reservas -H 'Content-Type: application/json' \
  -d '{"cancha_id":1,"cliente_id":1,"fecha_inicio":"2030-01-16T10:00:00","fecha_fin":"2030-01-16T12:00:00"}'
```
