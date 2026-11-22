from django.contrib import admin

from .models import Alerta, Camara, RegistroConteo


@admin.register(Camara)
class CamaraAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ubicacion", "fuente", "aforo_maximo", "activa")
    list_editable = ("aforo_maximo", "activa")
    search_fields = ("nombre", "ubicacion")


@admin.register(RegistroConteo)
class RegistroConteoAdmin(admin.ModelAdmin):
    list_display = ("camara", "cantidad", "fecha_hora")
    list_filter = ("camara", "fecha_hora")
    date_hierarchy = "fecha_hora"


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ("camara", "cantidad", "aforo_maximo", "fecha_hora", "atendida")
    list_filter = ("camara", "atendida")
    list_editable = ("atendida",)
