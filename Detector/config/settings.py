"""Configuración del proyecto Detector (conteo de personas en laboratorio)."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-clave-insegura-cambiar-en-produccion")
DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "conteo",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Base de datos: PostgreSQL (credenciales en el archivo .env)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "detector_db"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# Usar base de datos SQLite temporal solo para ejecutar las pruebas
if 'test' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-ec"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Parámetros del módulo de conteo de personas
# ---------------------------------------------------------------------------
MODELOS_DIR = BASE_DIR / "ml_models"

CONTEO = {
    # Modelo MobileNet-SSD (Caffe). Si no existe, se usa el detector HOG de OpenCV.
    "MODELO_PROTOTXT": MODELOS_DIR / "MobileNetSSD_deploy.prototxt",
    "MODELO_PESOS": MODELOS_DIR / "MobileNetSSD_deploy.caffemodel",
    "CONFIANZA": float(os.getenv("CONTEO_CONFIANZA", "0.5")),
    "UMBRAL_NMS": 0.4,
    # La detección corre en su propio hilo, como máximo una vez cada X segundos.
    # Valores más bajos = conteo más reactivo pero más uso de CPU.
    "DETECTAR_INTERVALO_SEG": float(os.getenv("CONTEO_INTERVALO_DETECCION", "0.5")),
    # Núcleos que puede usar OpenCV. 1 deja CPU libre para Django y el sistema.
    "HILOS_OPENCV": int(os.getenv("CONTEO_HILOS_OPENCV", "1")),
    # Cantidad de conteos usados para estabilizar el número (moda).
    "VENTANA_SUAVIZADO": 10,
    # Guardar en BD al menos cada X segundos (y también cuando el conteo cambie).
    "INTERVALO_REGISTRO_SEG": int(os.getenv("CONTEO_INTERVALO_REGISTRO", "10")),
    "MIN_SEG_ENTRE_CAMBIOS": 2,
    "COOLDOWN_ALERTA_SEG": 60,
    # Si nadie consulta la cámara durante X segundos, se libera.
    "INACTIVIDAD_SEG": 30,
    # Fuente por defecto: "0" = webcam integrada, o una URL RTSP/HTTP.
    "FUENTE_DEFAULT": os.getenv("CAMARA_FUENTE", "0"),
    "AFORO_DEFAULT": int(os.getenv("CAMARA_AFORO", "30")),
    "CALIDAD_JPEG": 80,
}