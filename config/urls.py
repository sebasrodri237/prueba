from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from pruebapp.views import ReunionViewSet
from pruebapp.views import whatsapp_webhook

router = DefaultRouter()
router.register(r'reuniones', ReunionViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/whatsapp-webhook/', whatsapp_webhook, name='whatsapp_webhook'),
]
