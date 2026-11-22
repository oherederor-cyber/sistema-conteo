"""Pruebas unitarias del detector (no necesitan base de datos ni cámara)."""
from unittest import TestCase

import numpy as np

from conteo.detector import (
    CLASE_PERSONA_VOC,
    ConteoSuavizado,
    Deteccion,
    PersonDetector,
    dibujar_resultados,
    frame_mensaje,
)


class RedFalsa:
    """Simula la salida de cv2.dnn: matriz (1, 1, N, 7) con
    [_, clase, confianza, x1, y1, x2, y2] en coordenadas normalizadas."""

    def __init__(self, filas):
        self.salida = np.array(filas, dtype=np.float32).reshape(1, 1, len(filas), 7)

    def setInput(self, blob):
        self.blob = blob

    def forward(self):
        return self.salida


def frame_negro(ancho=640, alto=480):
    return np.zeros((alto, ancho, 3), dtype=np.uint8)


class PersonDetectorDnnTests(TestCase):
    def test_cuenta_solo_la_clase_persona(self):
        red = RedFalsa([
            [0, CLASE_PERSONA_VOC, 0.90, 0.10, 0.10, 0.30, 0.80],
            [0, CLASE_PERSONA_VOC, 0.80, 0.60, 0.10, 0.80, 0.80],
            [0, 7, 0.95, 0.40, 0.40, 0.50, 0.50],  # clase 7 = auto
        ])
        detecciones = PersonDetector(net=red).detectar(frame_negro())
        self.assertEqual(len(detecciones), 2)

    def test_descarta_confianza_baja(self):
        red = RedFalsa([
            [0, CLASE_PERSONA_VOC, 0.30, 0.10, 0.10, 0.30, 0.80],
            [0, CLASE_PERSONA_VOC, 0.70, 0.60, 0.10, 0.80, 0.80],
        ])
        detecciones = PersonDetector(net=red, confianza=0.5).detectar(frame_negro())
        self.assertEqual(len(detecciones), 1)
        self.assertAlmostEqual(detecciones[0].confianza, 0.70, places=2)

    def test_nms_elimina_cajas_duplicadas(self):
        red = RedFalsa([
            [0, CLASE_PERSONA_VOC, 0.90, 0.10, 0.10, 0.40, 0.90],
            [0, CLASE_PERSONA_VOC, 0.85, 0.11, 0.11, 0.41, 0.91],  # misma persona
        ])
        self.assertEqual(len(PersonDetector(net=red).detectar(frame_negro())), 1)

    def test_convierte_coordenadas_a_pixeles(self):
        red = RedFalsa([[0, CLASE_PERSONA_VOC, 0.9, 0.25, 0.5, 0.5, 1.0]])
        det = PersonDetector(net=red).detectar(frame_negro(640, 480))[0]
        self.assertEqual((det.x, det.y), (160, 240))
        self.assertEqual(det.w, 160)

    def test_frame_vacio_devuelve_lista_vacia(self):
        red = RedFalsa([[0, CLASE_PERSONA_VOC, 0.9, 0.1, 0.1, 0.3, 0.8]])
        self.assertEqual(PersonDetector(net=red).detectar(np.array([])), [])


class PersonDetectorHogTests(TestCase):
    def test_sin_modelo_usa_hog(self):
        detector = PersonDetector("no_existe.prototxt", "no_existe.caffemodel")
        self.assertEqual(detector.modo, "HOG")

    def test_hog_en_imagen_vacia_cuenta_cero(self):
        detector = PersonDetector()
        self.assertEqual(detector.detectar(frame_negro()), [])


class ConteoSuavizadoTests(TestCase):
    def test_sin_valores_es_cero(self):
        self.assertEqual(ConteoSuavizado().valor, 0)

    def test_devuelve_la_moda(self):
        s = ConteoSuavizado(ventana=5)
        for v in [4, 5, 4, 4, 5]:
            s.agregar(v)
        self.assertEqual(s.valor, 4)

    def test_ventana_olvida_valores_antiguos(self):
        s = ConteoSuavizado(ventana=3)
        for v in [1, 1, 1, 3, 3, 3]:
            s.agregar(v)
        self.assertEqual(s.valor, 3)


class DibujoTests(TestCase):
    def test_dibujar_conserva_dimensiones_y_modifica_frame(self):
        frame = frame_negro()
        resultado = dibujar_resultados(frame, [Deteccion(10, 10, 50, 100, 0.9)], 1, aforo=5)
        self.assertEqual(resultado.shape, (480, 640, 3))
        self.assertGreater(resultado.sum(), 0)

    def test_frame_mensaje(self):
        self.assertEqual(frame_mensaje("Hola").shape, (480, 640, 3))
