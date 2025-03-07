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
from django.http import JsonResponse

@csrf_exempt
def whatsapp_webhook(request):
    if request.method == "POST":
        try:
            if request.content_type == "application/json":
                data = json.loads(request.body.decode("utf-8"))
            else:
                data = request.POST  # Twilio envía datos en este formato

            from_number = data.get("From", "")
            mensaje = data.get("Body", "").strip().lower()

            respuesta_texto = procesar_mensaje(mensaje)

            twilio_resp = MessagingResponse()
            twilio_resp.message(respuesta_texto)

            return HttpResponse(str(twilio_resp), content_type="text/xml")
        
        except json.JSONDecodeError:
            return JsonResponse({"error": "Formato JSON inválido"}, status=400)

    return JsonResponse({"mensaje": "🟢 Webhook activo."}, status=200)

def procesar_mensaje(data):
    solicitud = data.get("solicitud", "").lower()

    if solicitud == "crear_reunion":
        return crear_reunion(data)

    elif solicitud == "listar_reuniones":
        return listar_reuniones()
    
    elif solicitud == "cancelar_reunion":
        return cancelar_reunion(data)

    return "❌ No entiendo la solicitud. Prueba con JSON válido."


def crear_reunion(data):
    try:
        nombre = data.get("nombre", "Reunión sin título")  # Nombre opcional
        fecha = parse_date(data.get("fecha"))
        hora_inicio = parse_time(data.get("hora_inicio"))
        hora_fin = parse_time(data.get("hora_fin"))

        nueva_reunion = Reunion.objects.create(
            usuario_id=data.get("usuario_id", 1),
            nombre=nombre,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin
        )

        return f"✅ Reunión '{nombre}' creada el {fecha} de {hora_inicio} a {hora_fin}."

    except Exception as e:
        return f"⚠️ Error al crear la reunión: {str(e)}"


def listar_reuniones():
    reuniones = Reunion.objects.filter(usuario_id=1)
    if not reuniones.exists():
        return "🔍 No tienes reuniones programadas."

    reuniones_serializadas = ReunionSerializer(reuniones, many=True).data
    return json.dumps({"reuniones": reuniones_serializadas}, indent=2, ensure_ascii=False)

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
