from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse

from conteo.models import Alerta, Camara, RegistroConteo


class ModelosTests(TestCase):
    def test_fuente_numerica_se_convierte_a_entero(self):
        self.assertEqual(Camara(nombre="A", fuente="0").fuente_opencv, 0)

    def test_fuente_url_se_mantiene(self):
        url = "rtsp://192.168.1.10/stream"
        self.assertEqual(Camara(nombre="A", fuente=url).fuente_opencv, url)

    def test_str_registro(self):
        cam = Camara.objects.create(nombre="Lab 1")
        self.assertIn("Lab 1: 4 personas", str(RegistroConteo.objects.create(camara=cam, cantidad=4)))


class VistasTests(TestCase):
    def setUp(self):
        self.camara = Camara.objects.create(nombre="Lab", aforo_maximo=10)

    def test_inicio_redirige_al_dashboard(self):
        r = self.client.get(reverse("conteo:inicio"))
        self.assertRedirects(r, reverse("conteo:dashboard", args=[self.camara.pk]))

    def test_inicio_crea_camara_si_no_existe(self):
        Camara.objects.all().delete()
        self.client.get(reverse("conteo:inicio"))
        self.assertEqual(Camara.objects.count(), 1)

    def test_dashboard_muestra_camara(self):
        r = self.client.get(reverse("conteo:dashboard", args=[self.camara.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Personas en el laboratorio")
        self.assertContains(r, reverse("conteo:video_feed", args=[self.camara.pk]))

    def test_dashboard_camara_inexistente_404(self):
        self.assertEqual(self.client.get(reverse("conteo:dashboard", args=[999])).status_code, 404)

    @patch("conteo.views.gestor_camaras")
    def test_api_conteo_devuelve_estado(self, gestor):
        cam = MagicMock()
        cam.estado.return_value = {
            "cantidad": 3, "aforo": 10, "excedido": False, "fps": 15.0,
            "activa": True, "error": None, "detector": "MobileNet-SSD",
        }
        gestor.obtener.return_value = cam
        datos = self.client.get(reverse("conteo:api_conteo", args=[self.camara.pk])).json()
        self.assertEqual(datos["cantidad"], 3)
        self.assertEqual(datos["camara"], "Lab")
        self.assertIn("timestamp", datos)

    def test_api_historial_resumen(self):
        for n in (2, 4, 6):
            RegistroConteo.objects.create(camara=self.camara, cantidad=n)
        Alerta.objects.create(camara=self.camara, cantidad=12, aforo_maximo=10)
        datos = self.client.get(reverse("conteo:api_historial", args=[self.camara.pk])).json()
        self.assertEqual(len(datos["puntos"]), 3)
        self.assertEqual(datos["resumen"]["maximo"], 6)
        self.assertEqual(datos["resumen"]["promedio"], 4.0)
        self.assertEqual(datos["resumen"]["alertas"], 1)

    def test_api_historial_parametro_invalido(self):
        r = self.client.get(reverse("conteo:api_historial", args=[self.camara.pk]), {"horas": "abc"})
        self.assertEqual(r.json()["horas"], 1)

    def test_historial_pagina(self):
        r = self.client.get(reverse("conteo:historial", args=[self.camara.pk]))
        self.assertEqual(r.status_code, 200)
