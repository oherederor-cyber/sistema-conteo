"""Lógica de persistencia: decide cuándo guardar conteos y alertas en PostgreSQL."""
from __future__ import annotations

import logging
import time

from django.db import close_old_connections

from .models import Alerta, RegistroConteo

logger = logging.getLogger(__name__)


class RegistroService:
    """Guarda un registro cuando el conteo cambia o cada ``intervalo`` segundos.

    No se guarda cada frame: eso llenaría la base de datos de datos repetidos.
    """

    def __init__(
        self,
        camara_id: int,
        aforo: int,
        intervalo: float = 10,
        min_entre_cambios: float = 2,
        cooldown_alerta: float = 60,
        reloj=time.monotonic,
    ):
        self.camara_id = camara_id
        self.aforo = aforo
        self.intervalo = intervalo
        self.min_entre_cambios = min_entre_cambios
        self.cooldown_alerta = cooldown_alerta
        self._reloj = reloj
        self._ultimo_valor: int | None = None
        self._ultimo_registro = float("-inf")
        self._ultima_alerta = float("-inf")

    def debe_registrar(self, cantidad: int, ahora: float) -> bool:
        transcurrido = ahora - self._ultimo_registro
        if transcurrido >= self.intervalo:
            return True
        return cantidad != self._ultimo_valor and transcurrido >= self.min_entre_cambios

    def debe_alertar(self, cantidad: int, ahora: float) -> bool:
        return cantidad > self.aforo and (ahora - self._ultima_alerta) >= self.cooldown_alerta

    def procesar(self, cantidad: int) -> tuple[bool, bool]:
        """Devuelve (se_registró, se_generó_alerta)."""
        ahora = self._reloj()
        registrar = self.debe_registrar(cantidad, ahora)
        alertar = self.debe_alertar(cantidad, ahora)
        if not (registrar or alertar):
            return False, False

        close_old_connections()  # este código corre en el hilo de la cámara
        try:
            if registrar:
                RegistroConteo.objects.create(camara_id=self.camara_id, cantidad=cantidad)
                self._ultimo_valor = cantidad
                self._ultimo_registro = ahora
            if alertar:
                Alerta.objects.create(
                    camara_id=self.camara_id, cantidad=cantidad, aforo_maximo=self.aforo
                )
                self._ultima_alerta = ahora
        except Exception:  # la BD caída no debe detener el video
            logger.exception("No se pudo guardar el conteo en la base de datos")
            return False, False
        return registrar, alertar
