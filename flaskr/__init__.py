from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask


def create_app(config_name: str | None = None) -> Flask:
    """Application factory. `config_name`: 'dev' | 'test' (por defecto APP_ENV o 'dev')."""
    from dotenv import load_dotenv
    from flask import Flask, g, jsonify, render_template
    from werkzeug.exceptions import HTTPException

    from flaskr.application.ports.reservaUseCases import ReservaUseCases
    from flaskr.configuracion import obtener_config
    from flaskr.domain.services.reservaService import ReservaService
    from flaskr.infrastructure.adaptadorEntrada.reservaController import reservas_bp
    from flaskr.infrastructure.adaptadorSalida.reservaRepositorySQL import ReservaRepositorySQL
    from flaskr.infrastructure.db.engine import crear_engine
    from flaskr.infrastructure.db.session import crear_session_factory

    from flaskr.inicializarBD import crear_tablas  # import local: evita warning de `python -m flaskr.inicializarBD`

    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(obtener_config(config_name))

    engine = crear_engine(app.config["DATABASE_URL"])
    crear_tablas(engine)
    app.extensions["engine"] = engine
    app.extensions["session_factory"] = crear_session_factory(engine)

    def crear_servicio() -> ReservaUseCases:
        if "session" not in g:
            g.session = app.extensions["session_factory"]()
            g.servicio = ReservaService(
                ReservaRepositorySQL(g.session),
                hora_apertura=app.config["HORA_APERTURA"],
                hora_cierre=app.config["HORA_CIERRE"],
            )
        return g.servicio

    app.extensions["reserva_service_factory"] = crear_servicio

    @app.teardown_request
    def cerrar_sesion(_exc=None):
        session = g.pop("session", None)
        if session is not None:
            session.close()

    app.register_blueprint(reservas_bp)

    @app.get("/")
    def panel():
        return render_template("panel.html")

    @app.errorhandler(HTTPException)
    def _http_error(exc: HTTPException):
        return jsonify({"error": exc.description}), exc.code

    return app
