import time
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .camera import gestor_camaras
from .models import Alerta, Camara, RegistroConteo


def _camara_por_defecto():
    camara = Camara.objects.filter(activa=True).first()
    if camara is None:
        camara = Camara.objects.create(
            nombre="Laboratorio",
            ubicacion="Laboratorio de cómputo",
            fuente=settings.CONTEO["FUENTE_DEFAULT"],
            aforo_maximo=settings.CONTEO["AFORO_DEFAULT"],
        )
    return camara


def inicio(request):
    return redirect("conteo:dashboard", camara_id=_camara_por_defecto().pk)


def dashboard(request, camara_id):
    camara = get_object_or_404(Camara, pk=camara_id)
    return render(request, "conteo/dashboard.html", {
        "camara": camara,
        "camaras": Camara.objects.filter(activa=True),
        "alertas": camara.alertas.all()[:5],
    })


def _generar_mjpeg(cam):
    """Generador de frames JPEG para el stream multipart (MJPEG)."""
    ultimo_id = -1
    while True:
        frame_id, jpeg = cam.obtener_jpeg()
        if jpeg is None or frame_id == ultimo_id:
            time.sleep(0.01)
            continue
        ultimo_id = frame_id
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"


def video_feed(request, camara_id):
    camara = get_object_or_404(Camara, pk=camara_id, activa=True)
    cam = gestor_camaras.obtener(camara)
    respuesta = StreamingHttpResponse(
        _generar_mjpeg(cam), content_type="multipart/x-mixed-replace; boundary=frame"
    )
    respuesta["Cache-Control"] = "no-cache"
    return respuesta


def api_conteo(request, camara_id):
    camara = get_object_or_404(Camara, pk=camara_id, activa=True)
    datos = gestor_camaras.obtener(camara).estado()
    datos.update({"camara": camara.nombre, "timestamp": timezone.now().isoformat()})
    return JsonResponse(datos)


def historial(request, camara_id):
    camara = get_object_or_404(Camara, pk=camara_id)
    return render(request, "conteo/historial.html", {
        "camara": camara,
        "camaras": Camara.objects.filter(activa=True),
        "registros": camara.registros.all()[:50],
        "alertas": camara.alertas.all()[:20],
    })


def api_historial(request, camara_id):
    camara = get_object_or_404(Camara, pk=camara_id)
    try:
        horas = max(1, min(int(request.GET.get("horas", 1)), 168))
    except ValueError:
        horas = 1
    desde = timezone.now() - timedelta(hours=horas)
    registros = (
        RegistroConteo.objects.filter(camara=camara, fecha_hora__gte=desde)
        .order_by("fecha_hora")
        .values("fecha_hora", "cantidad")
    )
    puntos = [{"t": r["fecha_hora"].isoformat(), "y": r["cantidad"]} for r in registros]
    cantidades = [p["y"] for p in puntos]
    return JsonResponse({
        "camara": camara.nombre,
        "aforo": camara.aforo_maximo,
        "horas": horas,
        "puntos": puntos,
        "resumen": {
            "maximo": max(cantidades, default=0),
            "promedio": round(sum(cantidades) / len(cantidades), 1) if cantidades else 0,
            "registros": len(cantidades),
            "alertas": Alerta.objects.filter(camara=camara, fecha_hora__gte=desde).count(),
        },
    })
