from django.test import TestCase

from conteo.models import Alerta, Camara, RegistroConteo
from conteo.services import RegistroService


class RelojFalso:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class RegistroServiceTests(TestCase):
    def setUp(self):
        self.camara = Camara.objects.create(nombre="Lab", aforo_maximo=3)
        self.reloj = RelojFalso()
        self.servicio = RegistroService(
            self.camara.pk, aforo=3, intervalo=10, min_entre_cambios=2,
            cooldown_alerta=60, reloj=self.reloj,
        )

    def test_primer_conteo_siempre_se_registra(self):
        self.assertEqual(self.servicio.procesar(2), (True, False))
        self.assertEqual(RegistroConteo.objects.count(), 1)

    def test_mismo_valor_no_se_repite_antes_del_intervalo(self):
        self.servicio.procesar(2)
        self.reloj.t = 5
        self.servicio.procesar(2)
        self.assertEqual(RegistroConteo.objects.count(), 1)

    def test_mismo_valor_se_registra_al_cumplir_intervalo(self):
        self.servicio.procesar(2)
        self.reloj.t = 10
        self.servicio.procesar(2)
        self.assertEqual(RegistroConteo.objects.count(), 2)

    def test_cambio_de_valor_se_registra(self):
        self.servicio.procesar(2)
        self.reloj.t = 3
        self.servicio.procesar(1)
        self.assertEqual(
            list(RegistroConteo.objects.order_by("id").values_list("cantidad", flat=True)), [2, 1]
        )

    def test_alerta_al_superar_aforo_con_cooldown(self):
        self.servicio.procesar(5)
        self.reloj.t = 30
        self.servicio.procesar(5)
        self.assertEqual(Alerta.objects.count(), 1)
        self.reloj.t = 61
        self.servicio.procesar(5)
        self.assertEqual(Alerta.objects.count(), 2)

    def test_igual_al_aforo_no_genera_alerta(self):
        self.servicio.procesar(3)
        self.assertEqual(Alerta.objects.count(), 0)
