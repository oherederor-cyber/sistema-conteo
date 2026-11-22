from django.urls import path

from . import views

app_name = "conteo"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("camaras/<int:camara_id>/", views.dashboard, name="dashboard"),
    path("camaras/<int:camara_id>/video/", views.video_feed, name="video_feed"),
    path("camaras/<int:camara_id>/historial/", views.historial, name="historial"),
    path("api/camaras/<int:camara_id>/conteo/", views.api_conteo, name="api_conteo"),
    path("api/camaras/<int:camara_id>/historial/", views.api_historial, name="api_historial"),
]
