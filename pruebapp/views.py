from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.db.models import Q
from twilio.twiml.messaging_response import MessagingResponse
from .models import Reunion
from .serializers import ReunionSerializer

@permission_classes([AllowAny])
class ReunionViewSet(viewsets.ModelViewSet):
    queryset = Reunion.objects.all()
    serializer_class = ReunionSerializer

    def find_conflicts(self, usuario_id, fecha, hora_inicio, hora_fin, exclude_id=None):
        conflictos = Reunion.objects.filter(
            usuario_id=usuario_id,
            fecha=fecha
        ).filter(
            Q(hora_inicio__lt=hora_fin, hora_fin__gt=hora_inicio)
        )

        if exclude_id:
            conflictos = conflictos.exclude(id=exclude_id)

        return conflictos

def responder_sms(texto):
    """Genera una respuesta XML válida para Twilio."""
    respuesta = MessagingResponse()
    respuesta.message(texto)
    return HttpResponse(str(respuesta), content_type="application/xml")

@api_view(['POST'])
@permission_classes([AllowAny])
def procesar_solicitud(request):
    """Procesa los mensajes entrantes de WhatsApp y ejecuta la acción correspondiente."""
    data = request.data if request.content_type == "application/json" else request.POST
    mensaje = data.get("Body", "").strip().lower()

    if mensaje.startswith("agendar"):
        partes = mensaje.split(",")
        if len(partes) == 5:
            data = {
                "solicitud": "agendar",
                "nombre": partes[1].strip(),
                "fecha": partes[2].strip(),
                "hora_inicio": partes[3].strip(),
                "hora_fin": partes[4].strip()
            }
            return agendar_reunion(data)

    elif mensaje.startswith("modificar"):
        partes = mensaje.split(",")
        if len(partes) >= 2:
            data = {"solicitud": "modificar", "nombre": partes[1].strip()}
            if len(partes) == 5:
                data["fecha"] = partes[2].strip()
                data["hora_inicio"] = partes[3].strip()
                data["hora_fin"] = partes[4].strip()
            return modificar_reunion(data)

    elif mensaje.startswith("ver reuniones"):
        return ver_reuniones()

    elif mensaje.startswith("eliminar"):
        partes = mensaje.split(",")
        if len(partes) == 2:
            data = {"solicitud": "eliminar", "nombre": partes[1].strip()}
            return eliminar_reunion(data)

    return responder_sms("⚠️ Solicitud no reconocida.")

@permission_classes([AllowAny])
def agendar_reunion(data):
    serializer = ReunionSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return responder_sms("✅ Reunión creada exitosamente.")
    return responder_sms("⚠️ Error al crear la reunión.")

@permission_classes([AllowAny])
def modificar_reunion(data):
    try:
        reunion = Reunion.objects.get(nombre=data.get("nombre"))
        serializer = ReunionSerializer(reunion, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return responder_sms("✅ Reunión modificada exitosamente.")
        return responder_sms("⚠️ Error al modificar la reunión.")
    except Reunion.DoesNotExist:
        return responder_sms("⚠️ Reunión no encontrada.")

@permission_classes([AllowAny])
def ver_reuniones():
    reuniones = Reunion.objects.all()
    if not reuniones:
        return responder_sms("📅 No hay reuniones agendadas.")
    texto = "\n".join([f"{r.nombre} - {r.fecha} {r.hora_inicio}" for r in reuniones])
    return responder_sms(f"📅 Reuniones:\n{texto}")

@permission_classes([AllowAny])
def eliminar_reunion(data):
    try:
        reunion = Reunion.objects.get(nombre=data.get("nombre"))
        reunion.delete()
        return responder_sms("✅ Reunión eliminada exitosamente.")
    except Reunion.DoesNotExist:
        return responder_sms("⚠️ Reunión no encontrada.")

@api_view(['POST'])
@permission_classes([AllowAny])
def whatsapp_webhook(request):
    """Webhook de Twilio para recibir y procesar mensajes de WhatsApp."""
    return procesar_solicitud(request)
