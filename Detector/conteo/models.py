from django.db import models


class Camara(models.Model):
    nombre = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=150, blank=True)
    fuente = models.CharField(
        max_length=255,
        default="0",
        help_text='Índice de la webcam ("0", "1"...) o URL RTSP/HTTP de una cámara IP.',
    )
    aforo_maximo = models.PositiveIntegerField(default=30)
    activa = models.BooleanField(default=True)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "cámara"
        verbose_name_plural = "cámaras"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.ubicacion})" if self.ubicacion else self.nombre

    @property
    def fuente_opencv(self):
        """Convierte la fuente al tipo que espera cv2.VideoCapture."""
        return int(self.fuente) if self.fuente.strip().isdigit() else self.fuente.strip()


class RegistroConteo(models.Model):
    camara = models.ForeignKey(Camara, on_delete=models.CASCADE, related_name="registros")
    cantidad = models.PositiveIntegerField()
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "registro de conteo"
        verbose_name_plural = "registros de conteo"
        ordering = ["-fecha_hora"]

    def __str__(self):
        return f"{self.camara.nombre}: {self.cantidad} personas @ {self.fecha_hora:%Y-%m-%d %H:%M:%S}"


class Alerta(models.Model):
    camara = models.ForeignKey(Camara, on_delete=models.CASCADE, related_name="alertas")
    cantidad = models.PositiveIntegerField()
    aforo_maximo = models.PositiveIntegerField()
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)
    atendida = models.BooleanField(default=False)

    class Meta:
        verbose_name = "alerta de aforo"
        verbose_name_plural = "alertas de aforo"
        ordering = ["-fecha_hora"]

    def __str__(self):
        return f"Aforo excedido en {self.camara.nombre}: {self.cantidad}/{self.aforo_maximo}"
