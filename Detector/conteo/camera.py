"""Captura de video y detección en hilos en segundo plano.

Por cada cámara hay dos hilos:
  * Captura: lee frames, dibuja las últimas detecciones y guarda el último
    JPEG. Nunca espera a la red neuronal, así el video se mantiene fluido.
  * Detección: toma el frame más reciente y ejecuta el detector como máximo
    una vez cada ``DETECTAR_INTERVALO_SEG`` segundos, para no saturar la CPU.

Las vistas de Django solo leen ese JPEG, así varias pestañas del navegador
pueden ver el mismo video sin abrir la cámara varias veces.
"""
from __future__ import annotations

import logging
import os
import threading
import time

import cv2
from django.conf import settings

from .detector import ConteoSuavizado, PersonDetector, dibujar_resultados, frame_mensaje

logger = logging.getLogger(__name__)

# OpenCV usa por defecto todos los núcleos; limitarlo deja CPU libre para Django.
cv2.setNumThreads(settings.CONTEO.get("HILOS_OPENCV", 1))


def _abrir_captura(fuente):
    # En Windows, CAP_DSHOW abre la webcam mucho más rápido.
    if isinstance(fuente, int) and os.name == "nt":
        return cv2.VideoCapture(fuente, cv2.CAP_DSHOW)
    return cv2.VideoCapture(fuente)


class VideoCamera:
    def __init__(self, camara_id, fuente, aforo, detector, registro=None, config=None):
        cfg = config or settings.CONTEO
        self.camara_id = camara_id
        self.fuente = fuente
        self.aforo = aforo
        self.detector = detector
        self.registro = registro
        self.intervalo_deteccion = max(0.0, cfg["DETECTAR_INTERVALO_SEG"])
        self.inactividad = cfg["INACTIVIDAD_SEG"]
        self.calidad_jpeg = cfg["CALIDAD_JPEG"]
        self.suavizado = ConteoSuavizado(cfg["VENTANA_SUAVIZADO"])

        self._lock = threading.Lock()
        self._hilo: threading.Thread | None = None
        self._hilo_deteccion: threading.Thread | None = None
        self._corriendo = False
        self._nuevo_frame = threading.Event()
        self._frame_pendiente = None  # último frame sin procesar por el detector
        self._detecciones = []
        self._jpeg: bytes | None = None
        self._frame_id = 0
        self._cantidad = 0
        self._fps = 0.0
        self._error: str | None = None
        self._ultimo_acceso = time.monotonic()

    # ------------------------------------------------------------ control
    @property
    def corriendo(self) -> bool:
        return self._corriendo and self._hilo is not None and self._hilo.is_alive()

    def iniciar(self):
        with self._lock:
            if self.corriendo:
                return
            self._corriendo = True
            self._ultimo_acceso = time.monotonic()
            self._hilo = threading.Thread(
                target=self._bucle, name=f"camara-{self.camara_id}", daemon=True
            )
            self._hilo.start()
            # Si el hilo de detección anterior sigue vivo (reinicio rápido), se
            # reutiliza: el detector de cv2.dnn no se puede usar desde dos hilos.
            if self._hilo_deteccion is None or not self._hilo_deteccion.is_alive():
                self._hilo_deteccion = threading.Thread(
                    target=self._bucle_deteccion, name=f"deteccion-{self.camara_id}", daemon=True
                )
                self._hilo_deteccion.start()

    def detener(self):
        self._corriendo = False
        self._nuevo_frame.set()

    def tocar(self):
        """Marca que alguien sigue usando la cámara (evita que se libere)."""
        self._ultimo_acceso = time.monotonic()

    # ------------------------------------------------------------ lectura
    def obtener_jpeg(self) -> tuple[int, bytes | None]:
        self.tocar()
        with self._lock:
            return self._frame_id, self._jpeg

    def estado(self) -> dict:
        self.tocar()
        with self._lock:
            return {
                "cantidad": self._cantidad,
                "aforo": self.aforo,
                "excedido": self._cantidad > self.aforo,
                "fps": round(self._fps, 1),
                "activa": self.corriendo and self._error is None,
                "error": self._error,
                "detector": self.detector.modo,
            }

    # ------------------------------------------------------------ hilo
    def _publicar(self, frame, cantidad=None, error=None):
        ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.calidad_jpeg])
        with self._lock:
            if ok:
                self._jpeg = buffer.tobytes()
                self._frame_id += 1
            if cantidad is not None:
                self._cantidad = cantidad
            self._error = error

    def _bucle_deteccion(self):
        """Ejecuta el detector sobre el frame más reciente, sin bloquear la captura."""
        try:
            while self._corriendo:
                if not self._nuevo_frame.wait(timeout=1.0):
                    continue
                self._nuevo_frame.clear()
                with self._lock:
                    frame, self._frame_pendiente = self._frame_pendiente, None
                if frame is None:
                    continue

                inicio = time.monotonic()
                detecciones = self.detector.detectar(frame)
                cantidad = self.suavizado.agregar(len(detecciones))
                with self._lock:
                    self._detecciones = detecciones
                if self.registro is not None:
                    self.registro.aforo = self.aforo
                    self.registro.procesar(cantidad)

                espera = self.intervalo_deteccion - (time.monotonic() - inicio)
                if espera > 0:
                    time.sleep(espera)
        except Exception:
            logger.exception("Error en el hilo de detección de la cámara %s", self.camara_id)

    def _bucle(self):
        captura = _abrir_captura(self.fuente)
        t_fps, frames_fps = time.monotonic(), 0

        try:
            while self._corriendo:
                if time.monotonic() - self._ultimo_acceso > self.inactividad:
                    logger.info("Cámara %s liberada por inactividad", self.camara_id)
                    break

                ok, frame = captura.read() if captura.isOpened() else (False, None)
                if not ok:
                    self._publicar(frame_mensaje("Camara no disponible"), error="Cámara no disponible")
                    captura.release()
                    time.sleep(2)
                    captura = _abrir_captura(self.fuente)
                    continue

                # Entregar una copia al hilo de detección (se descartan los
                # frames que no alcance a procesar).
                with self._lock:
                    self._frame_pendiente = frame.copy()
                    detecciones = self._detecciones
                self._nuevo_frame.set()
                cantidad = self.suavizado.valor

                dibujar_resultados(frame, detecciones, cantidad, self.aforo)
                self._publicar(frame, cantidad=cantidad)

                frames_fps += 1
                transcurrido = time.monotonic() - t_fps
                if transcurrido >= 1.0:
                    self._fps = frames_fps / transcurrido
                    t_fps, frames_fps = time.monotonic(), 0
        except Exception:
            logger.exception("Error en el hilo de la cámara %s", self.camara_id)
        finally:
            captura.release()
            self._corriendo = False
            self._nuevo_frame.set()  # despierta al hilo de detección para que termine


class GestorCamaras:
    """Mantiene una sola instancia de VideoCamera por cámara (singleton por id)."""

    def __init__(self):
        self._camaras: dict[int, VideoCamera] = {}
        self._lock = threading.Lock()

    def obtener(self, camara) -> VideoCamera:
        from .services import RegistroService

        cfg = settings.CONTEO
        with self._lock:
            cam = self._camaras.get(camara.pk)
            if cam is None or cam.fuente != camara.fuente_opencv:
                if cam is not None:
                    cam.detener()
                # cv2.dnn no es seguro entre hilos: un detector por cámara.
                detector = PersonDetector(
                    cfg["MODELO_PROTOTXT"], cfg["MODELO_PESOS"],
                    confianza=cfg["CONFIANZA"], umbral_nms=cfg["UMBRAL_NMS"],
                )
                registro = RegistroService(
                    camara.pk, camara.aforo_maximo,
                    intervalo=cfg["INTERVALO_REGISTRO_SEG"],
                    min_entre_cambios=cfg["MIN_SEG_ENTRE_CAMBIOS"],
                    cooldown_alerta=cfg["COOLDOWN_ALERTA_SEG"],
                )
                cam = VideoCamera(camara.pk, camara.fuente_opencv, camara.aforo_maximo, detector, registro)
                self._camaras[camara.pk] = cam
            cam.aforo = camara.aforo_maximo  # refleja cambios hechos en el admin
        cam.iniciar()
        return cam


gestor_camaras = GestorCamaras()
