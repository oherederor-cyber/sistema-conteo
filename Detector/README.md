# Detector — Conteo de personas en el laboratorio

Aplicación web en **Django** que captura video en tiempo real, detecta personas con **OpenCV** y muestra cuántas hay en el laboratorio. Los conteos y las alertas de aforo se guardan en **PostgreSQL**.

## Funcionalidades

- Transmisión de video en vivo (MJPEG) con las personas detectadas enmarcadas.
- Contador en pantalla, estabilizado con la moda de los últimos conteos.
- Control de aforo: barra de ocupación y alerta cuando se supera el máximo.
- Historial con gráfica (1 h, 8 h, 24 h, 7 días), máximo, promedio y alertas.
- Administración de cámaras (webcam o cámara IP RTSP/HTTP) desde el panel de Django.

## Arquitectura

```
Cámara ─▶ VideoCamera (hilo) ─▶ PersonDetector (cv2.dnn MobileNet-SSD)
                │                    └─ respaldo: HOG de OpenCV
                ├─▶ /camaras/<id>/video/          stream MJPEG
                ├─▶ /api/camaras/<id>/conteo/     JSON en vivo
                └─▶ RegistroService ─▶ PostgreSQL (RegistroConteo, Alerta)
```

| Archivo | Responsabilidad |
|---|---|
| `conteo/detector.py` | Detección de personas, NMS, suavizado y dibujo. Solo usa OpenCV y NumPy, sin Django. |
| `conteo/camera.py` | Hilo de captura y una sola instancia por cámara (`GestorCamaras`). |
| `conteo/services.py` | Decide cuándo guardar registros y alertas en la base de datos. |
| `conteo/models.py` | `Camara`, `RegistroConteo`, `Alerta`. |
| `conteo/views.py` | Dashboard, stream, historial y API JSON. |
| `conteo/tests/` | Pruebas unitarias y de integración. |

## Requisitos

- Python 3.10 o superior
- PostgreSQL 14 o superior (o Docker)
- Una webcam

## Instalación

```bash
git clone <URL-del-repositorio>
cd Detector

python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 1. Base de datos

Con Docker:

```bash
docker compose up -d
```

Sin Docker, crear la base de datos manualmente:

```sql
CREATE DATABASE detector_db;
```

### 2. Variables de entorno

Copiar `.env.example` como `.env` y ajustar las credenciales:

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

### 3. Modelo de detección

```bash
python ml_models/descargar_modelo.py
```

> Si no se descarga el modelo, el sistema funciona igual con el detector HOG de OpenCV, aunque es menos preciso.

### 4. Migraciones y usuario administrador

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Ejecutar

```bash
python manage.py runserver
```

Abrir <http://127.0.0.1:8000/>. La primera vez se crea automáticamente la cámara "Laboratorio" con la webcam `0`. El aforo y la fuente se cambian en <http://127.0.0.1:8000/admin/>.

## Pruebas

```bash
python manage.py test conteo
```

Qué se prueba:

- **Detector**: filtra solo la clase persona, aplica el umbral de confianza, elimina duplicados con NMS, convierte coordenadas, usa HOG como respaldo y cuenta 0 en una imagen vacía.
- **Suavizado**: calcula la moda y respeta la ventana.
- **RegistroService**: registra al cambiar el valor o al cumplir el intervalo, y genera alertas de aforo con *cooldown*.
- **Vistas y API**: redirecciones, 404, JSON en vivo y resumen del historial.

## Configuración

Parámetros en `config/settings.py`, sección `CONTEO`. Algunos se pueden cambiar desde `.env`:

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `CAMARA_FUENTE` | Índice de la webcam o URL | `0` |
| `CAMARA_AFORO` | Aforo de la cámara creada automáticamente | `30` |
| `CONTEO_CONFIANZA` | Confianza mínima de detección | `0.5` |
| `CONTEO_INTERVALO_DETECCION` | Segundos mínimos entre detecciones (más bajo = más CPU) | `0.5` |
| `CONTEO_HILOS_OPENCV` | Núcleos de CPU que usa OpenCV | `1` |
| `CONTEO_INTERVALO_REGISTRO` | Segundos entre registros si el conteo no cambia | `10` |

## Tecnologías

Python · Django · OpenCV (`cv2.dnn`, HOG) · NumPy · PostgreSQL · Bootstrap 5 · Chart.js · Docker
