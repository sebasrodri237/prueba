from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from pruebapp.views import ReunionViewSet  # Importa la vista correctamente

# Crea un router y registra la vista
router = DefaultRouter()
router.register(r'reuniones', ReunionViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),  # Incluye las rutas de DRF
]
