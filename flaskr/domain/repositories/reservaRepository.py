"""Contrato de persistencia requerido por la lógica de reservas."""
from abc import ABC, abstractmethod
from datetime import date, datetime

from flaskr.domain.models.cancha import Cancha, Deporte
from flaskr.domain.models.cliente import Cliente
from flaskr.domain.models.reserva import EstadoReserva, Reserva


class ReservaRepository(ABC):
    @abstractmethod
    def guardar(self, reserva: Reserva) -> Reserva:
        """Persiste una reserva nueva y la devuelve con su id asignado."""

    @abstractmethod
    def obtener_por_id(self, reserva_id: int) -> Reserva | None:
        """Devuelve la reserva o None si no existe."""

    @abstractmethod
    def listar(
        self,
        cancha_id: int | None = None,
        cliente_id: int | None = None,
        fecha: date | None = None,
        estado: EstadoReserva | None = None,
    ) -> list[Reserva]:
        """Lista reservas aplicando los filtros recibidos (fecha = día de inicio)."""

    @abstractmethod
    def buscar_cruces(self, cancha_id: int, inicio: datetime, fin: datetime) -> list[Reserva]:
        """Reservas no canceladas de la cancha que se solapan con [inicio, fin)."""

    @abstractmethod
    def actualizar(self, reserva: Reserva) -> Reserva:
        """Guarda los cambios de una reserva existente."""

    @abstractmethod
    def obtener_cancha(self, cancha_id: int) -> Cancha | None:
        """Devuelve la cancha o None si no existe."""

    @abstractmethod
    def obtener_cliente(self, cliente_id: int) -> Cliente | None:
        """Devuelve el cliente o None si no existe."""

    @abstractmethod
    def listar_canchas(self, deporte: Deporte | None = None) -> list[Cancha]:
        """Lista las canchas activas, opcionalmente filtradas por deporte."""

    @abstractmethod
    def buscar_clientes(self, texto: str) -> list[Cliente]:
        """Busca clientes por coincidencia parcial en nombre o documento."""
