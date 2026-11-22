"""Módulo de detección de personas.

No depende de Django: recibe un frame (matriz NumPy BGR de OpenCV) y devuelve
las detecciones. Esto permite probarlo de forma aislada (TDD).

Estrategia:
  * Principal: MobileNet-SSD (Caffe) cargado con ``cv2.dnn``, filtrando la
    clase "person" (índice 15 del conjunto PASCAL VOC).
  * Respaldo: detector HOG + SVM incluido en OpenCV, por si los pesos del
    modelo aún no se han descargado.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

CLASE_PERSONA_VOC = 15
TAMANO_ENTRADA_SSD = (300, 300)
FACTOR_ESCALA_SSD = 0.007843  # 1 / 127.5
MEDIA_SSD = 127.5


@dataclass(frozen=True)
class Deteccion:
    """Caja delimitadora de una persona detectada."""

    x: int
    y: int
    w: int
    h: int
    confianza: float

    @property
    def caja(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.w, self.h


class PersonDetector:
    """Detecta personas en un frame usando OpenCV."""

    def __init__(
        self,
        prototxt: str | Path | None = None,
        pesos: str | Path | None = None,
        confianza: float = 0.5,
        umbral_nms: float = 0.4,
        net=None,
    ):
        self.confianza = confianza
        self.umbral_nms = umbral_nms
        self.hog = None

        if net is not None:
            self.net = net
        elif prototxt and pesos and Path(prototxt).exists() and Path(pesos).exists():
            self.net = cv2.dnn.readNetFromCaffe(str(prototxt), str(pesos))
        else:
            self.net = None
            self.hog = cv2.HOGDescriptor()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    @property
    def modo(self) -> str:
        return "MobileNet-SSD" if self.net is not None else "HOG"

    def detectar(self, frame: np.ndarray) -> list[Deteccion]:
        if frame is None or frame.size == 0:
            return []
        if self.net is not None:
            return self._detectar_dnn(frame)
        return self._detectar_hog(frame)

    # ------------------------------------------------------------------ DNN
    def _detectar_dnn(self, frame: np.ndarray) -> list[Deteccion]:
        alto, ancho = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, TAMANO_ENTRADA_SSD),
            FACTOR_ESCALA_SSD,
            TAMANO_ENTRADA_SSD,
            MEDIA_SSD,
        )
        self.net.setInput(blob)
        salida = self.net.forward()  # forma: (1, 1, N, 7)

        cajas: list[list[int]] = []
        confianzas: list[float] = []
        escala = np.array([ancho, alto, ancho, alto])
        for i in range(salida.shape[2]):
            clase = int(salida[0, 0, i, 1])
            conf = float(salida[0, 0, i, 2])
            if clase != CLASE_PERSONA_VOC or conf < self.confianza:
                continue
            x1, y1, x2, y2 = (salida[0, 0, i, 3:7] * escala).astype(int)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(ancho - 1, x2), min(alto - 1, y2)
            if x2 <= x1 or y2 <= y1:
                continue
            cajas.append([int(x1), int(y1), int(x2 - x1), int(y2 - y1)])
            confianzas.append(conf)

        return self._aplicar_nms(cajas, confianzas, self.confianza)

    # ------------------------------------------------------------------ HOG
    def _detectar_hog(self, frame: np.ndarray) -> list[Deteccion]:
        alto, ancho = frame.shape[:2]
        escala = 1.0
        if ancho > 640:  # reducir para ganar velocidad
            escala = 640 / ancho
            frame = cv2.resize(frame, (640, int(alto * escala)))

        rects, pesos = self.hog.detectMultiScale(
            frame, winStride=(8, 8), padding=(8, 8), scale=1.05
        )
        if len(rects) == 0:
            return []
        cajas = [[int(v / escala) for v in r] for r in rects]
        confianzas = [float(p) for p in np.array(pesos).flatten()]
        return self._aplicar_nms(cajas, confianzas, 0.0)

    # ------------------------------------------------------------------ NMS
    def _aplicar_nms(self, cajas, confianzas, umbral_conf) -> list[Deteccion]:
        """Elimina cajas superpuestas que corresponden a la misma persona."""
        if not cajas:
            return []
        indices = cv2.dnn.NMSBoxes(cajas, confianzas, umbral_conf, self.umbral_nms)
        return [
            Deteccion(*cajas[i], confianza=confianzas[i])
            for i in np.array(indices).flatten()
        ]


class ConteoSuavizado:
    """Estabiliza el conteo usando la moda de los últimos valores.

    Evita que el número mostrado "parpadee" (p. ej. 4, 5, 4, 5) cuando una
    persona queda parcialmente oculta durante algunos frames.
    """

    def __init__(self, ventana: int = 10):
        self._valores: deque[int] = deque(maxlen=ventana)

    def agregar(self, valor: int) -> int:
        self._valores.append(valor)
        return self.valor

    @property
    def valor(self) -> int:
        if not self._valores:
            return 0
        return Counter(self._valores).most_common(1)[0][0]


COLOR_NORMAL = (0, 200, 0)
COLOR_EXCESO = (0, 0, 255)


def dibujar_resultados(
    frame: np.ndarray, detecciones: list[Deteccion], cantidad: int, aforo: int | None = None
) -> np.ndarray:
    """Dibuja las cajas y el contador sobre el frame (modifica y devuelve el frame)."""
    excedido = aforo is not None and cantidad > aforo
    color = COLOR_EXCESO if excedido else COLOR_NORMAL

    for det in detecciones:
        x, y, w, h = det.caja
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        cv2.putText(
            frame, f"{det.confianza:.0%}", (x, max(15, y - 6)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA,
        )

    texto = f"Personas: {cantidad}" + (f" / {aforo}" if aforo else "")
    (tw, th), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
    cv2.rectangle(frame, (10, 10), (20 + tw, 25 + th), (0, 0, 0), -1)
    cv2.putText(
        frame, texto, (15, 18 + th),
        cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2, cv2.LINE_AA,
    )
    if excedido:
        cv2.putText(
            frame, "AFORO EXCEDIDO", (15, 55 + th),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLOR_EXCESO, 2, cv2.LINE_AA,
        )
    return frame


def frame_mensaje(texto: str, ancho: int = 640, alto: int = 480) -> np.ndarray:
    """Genera una imagen negra con un mensaje (p. ej. cámara no disponible)."""
    frame = np.zeros((alto, ancho, 3), dtype=np.uint8)
    (tw, th), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
    cv2.putText(
        frame, texto, ((ancho - tw) // 2, (alto + th) // 2),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA,
    )
    return frame
