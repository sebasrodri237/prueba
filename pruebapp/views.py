from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.messaging_response import MessagingResponse
from .models import Reunion
from .serializers import ReunionSerializer
from django.utils.dateparse import parse_date, parse_time
import json
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db.models import Q

@csrf_exempt
def whatsapp_webhook(request):
    if request.method == "POST":
        from_number = request.POST.get("From")  # Número del usuario
        mensaje = request.POST.get("Body", "").strip().lower()  # Mensaje recibido

        respuesta_texto = procesar_mensaje(mensaje)

        twilio_resp = MessagingResponse()
        twilio_resp.message(respuesta_texto)
        
        return HttpResponse(str(twilio_resp), content_type="text/xml")  # ⬅️ Cambio importante

    return HttpResponse("🟢 Webhook activo.", content_type="text/plain")

def procesar_mensaje(mensaje):
    """ Analiza el mensaje y ejecuta la acción correspondiente """
    if "crear reunión" in mensaje:
        return crear_reunion(mensaje)

    elif "listar reuniones" in mensaje:
        return listar_reuniones()

    elif "cancelar reunión" in mensaje:
        return cancelar_reunion(mensaje)

    return "❌ No entiendo el mensaje. Prueba con: 'crear reunión', 'listar reuniones', 'cancelar reunión'."

def crear_reunion(mensaje):
    try:
        partes = mensaje.split()
        fecha = parse_date(partes[2])
        hora_inicio = parse_time(partes[3])
        hora_fin = parse_time(partes[4])

        Reunion.objects.create(
            usuario_id=1,  # Aquí podrías enlazar con el número de WhatsApp del usuario
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin
        )

        return f"✅ Reunión creada el {fecha} de {hora_inicio} a {hora_fin}."

    except Exception as e:
        return f"⚠️ Error al crear la reunión: {str(e)}"

def listar_reuniones():
    reuniones = Reunion.objects.filter(usuario_id=1)
    if not reuniones.exists():
        return "🔍 No tienes reuniones programadas."

    reuniones_serializadas = ReunionSerializer(reuniones, many=True).data
    return f"📅 Tus reuniones: {json.dumps(reuniones_serializadas, indent=2)}"

def cancelar_reunion(mensaje):
    try:
        partes = mensaje.split()
        reunion_id = int(partes[2])
        Reunion.objects.get(id=reunion_id, usuario_id=1).delete()
        return f"🗑️ Reunión {reunion_id} cancelada con éxito."

    except Reunion.DoesNotExist:
        return "⚠️ No se encontró la reunión."

    except Exception as e:
        return f"⚠️ Error al cancelar reunión: {str(e)}"

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

    def list(self, request, *args, **kwargs):
        nombre = request.query_params.get("nombre", None)
        fecha = request.query_params.get("fecha", None)
        hora = request.query_params.get("hora", None)

        queryset = self.queryset
        if nombre:
            queryset = queryset.filter(nombre__icontains=nombre)
        if fecha and not hora:
            queryset = queryset.filter(fecha=fecha)
        if fecha and hora:
            queryset = queryset.filter(fecha=fecha, hora_inicio=hora)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        user_id = request.data.get("usuario")
        fecha = request.data.get("fecha")
        hora_inicio = request.data.get("hora_inicio")
        hora_fin = request.data.get("hora_fin")

        conflictos = self.find_conflicts(user_id, fecha, hora_inicio, hora_fin)

        if conflictos.exists():
            conflictos_serializados = ReunionSerializer(conflictos, many=True).data
            return Response({
                "status": "⚠️ Conflicto de horario detectado.",
                "conflictos": conflictos_serializados
            }, status=status.HTTP_400_BAD_REQUEST)

        response = super().create(request, *args, **kwargs)

        return Response({
            "mensaje": "✅ Reunión creada exitosamente.",
            "reunion": response.data
        }, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        user_id = request.data.get("usuario", instance.usuario_id)
        fecha = request.data.get("fecha", instance.fecha)
        hora_inicio = request.data.get("hora_inicio", instance.hora_inicio)
        hora_fin = request.data.get("hora_fin", instance.hora_fin)

        conflictos = self.find_conflicts(user_id, fecha, hora_inicio, hora_fin, exclude_id=instance.id)

        if conflictos.exists():
            conflictos_serializados = ReunionSerializer(conflictos, many=True).data
            return Response({
                "status": "⚠️ Conflicto de horario detectado.",
                "conflictos": conflictos_serializados
            }, status=status.HTTP_400_BAD_REQUEST)

        response = super().update(request, *args, **kwargs)

        return Response({
            "mensaje": "✅ Reunión modificada exitosamente.",
            "reunion": response.data
        }, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        response = super().destroy(request, *args, **kwargs)

        return Response({
            "mensaje": "✅ Reunión eliminada exitosamente.",
            "reunion": {"id": instance.id, "nombre": instance.nombre, "fecha": instance.fecha}
        }, status=status.HTTP_200_OK)
