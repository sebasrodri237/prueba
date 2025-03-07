from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from pruebapp.views import ReunionViewSet, procesar_solicitud

router = DefaultRouter()
router.register(r'reuniones', ReunionViewSet)

urlpatterns = [
    path("api/whatsapp-webhook/", procesar_solicitud, name="whatsapp-webhook"),
]
