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
