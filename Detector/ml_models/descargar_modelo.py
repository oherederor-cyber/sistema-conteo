"""Descarga el modelo preentrenado MobileNet-SSD (Caffe, PASCAL VOC).

Uso:  python ml_models/descargar_modelo.py
"""
import sys
import urllib.request
from pathlib import Path

DESTINO = Path(__file__).resolve().parent
BASE = "https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/"
ARCHIVOS = {
    "MobileNetSSD_deploy.prototxt": BASE + "deploy.prototxt",
    "MobileNetSSD_deploy.caffemodel": BASE + "mobilenet_iter_73000.caffemodel",
}


def main():
    for nombre, url in ARCHIVOS.items():
        ruta = DESTINO / nombre
        if ruta.exists() and ruta.stat().st_size > 0:
            print(f"[ok] {nombre} ya existe")
            continue
        print(f"[..] Descargando {nombre} ...")
        try:
            urllib.request.urlretrieve(url, ruta)
        except Exception as exc:
            print(f"[x] Error al descargar {url}: {exc}")
            sys.exit(1)
        print(f"[ok] {nombre} ({ruta.stat().st_size / 1e6:.1f} MB)")
    print("Modelo listo.")


if __name__ == "__main__":
    main()
