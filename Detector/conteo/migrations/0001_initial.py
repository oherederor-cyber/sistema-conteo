import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Camara",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=100)),
                ("ubicacion", models.CharField(blank=True, max_length=150)),
                ("fuente", models.CharField(default="0", help_text='Índice de la webcam ("0", "1"...) o URL RTSP/HTTP de una cámara IP.', max_length=255)),
                ("aforo_maximo", models.PositiveIntegerField(default=30)),
                ("activa", models.BooleanField(default=True)),
                ("creada", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "cámara",
                "verbose_name_plural": "cámaras",
                "ordering": ["nombre"],
            },
        ),
        migrations.CreateModel(
            name="RegistroConteo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cantidad", models.PositiveIntegerField()),
                ("fecha_hora", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("camara", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="registros", to="conteo.camara")),
            ],
            options={
                "verbose_name": "registro de conteo",
                "verbose_name_plural": "registros de conteo",
                "ordering": ["-fecha_hora"],
            },
        ),
        migrations.CreateModel(
            name="Alerta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cantidad", models.PositiveIntegerField()),
                ("aforo_maximo", models.PositiveIntegerField()),
                ("fecha_hora", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("atendida", models.BooleanField(default=False)),
                ("camara", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alertas", to="conteo.camara")),
            ],
            options={
                "verbose_name": "alerta de aforo",
                "verbose_name_plural": "alertas de aforo",
                "ordering": ["-fecha_hora"],
            },
        ),
    ]
