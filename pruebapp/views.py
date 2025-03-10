from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.messaging_response import MessagingResponse
from .models import Reunion
from .serializers import ReunionSerializer
from django.utils.dateparse import parse_date, parse_time
import json
from django.db.models import Q

@csrf_exempt
def whatsapp_webhook(request):
    if request.method == "POST":
        try:
            if request.content_type == "application/json":
                data = json.loads(request.body.decode("utf-8"))
            else:
                data = request.POST.dict()

            solicitud = data.get("solicitud", "").lower()

            if solicitud == "agendar":
                respuesta = agendar_reunion(data)
            elif solicitud == "listar":
                respuesta = listar_reuniones(data)
            elif solicitud == "editar":
                respuesta = editar_reunion(data)
            elif solicitud == "eliminar":
                respuesta = eliminar_reunion(data)
            else:
                respuesta = "❌ Solicitud no reconocida."

        except json.JSONDecodeError:
            respuesta = "⚠️ Error: El formato del mensaje no es un JSON válido."

        twilio_resp = MessagingResponse()
        twilio_resp.message(respuesta)

        return HttpResponse(str(twilio_resp), content_type="text/xml")

    return HttpResponse("🟢 Webhook activo.", content_type="text/plain")

def agendar_reunion(data):
    try:
        nombre = data.get("nombre", "")
        fecha = parse_date(data.get("fecha", ""))
        hora_inicio = parse_time(data.get("hora_inicio", ""))
        hora_fin = parse_time(data.get("hora_fin", ""))

        if not (nombre and fecha and hora_inicio and hora_fin):
            return "⚠️ Datos insuficientes. Debes incluir nombre, fecha, hora de inicio y fin."

        conflictos = Reunion.objects.filter(
            fecha=fecha,
            hora_inicio__lt=hora_fin,
            hora_fin__gt=hora_inicio
        )

        if conflictos.exists():
            return "⚠️ No se puede agendar. Ya hay una reunión en ese horario."

        Reunion.objects.create(
            nombre=nombre,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin
        )

        return f"✅ Reunión '{nombre}' agendada para el {fecha} de {hora_inicio} a {hora_fin}."

    except Exception as e:
        return f"⚠️ Error al agendar la reunión: {str(e)}"

def listar_reuniones(data):
    try:
        reuniones = Reunion.objects.all()
        if not reuniones.exists():
            return "🔍 No hay reuniones programadas."

        reuniones_serializadas = ReunionSerializer(reuniones, many=True).data
        return f"📅 Reuniones:\n{json.dumps(reuniones_serializadas, indent=2)}"

    except Exception as e:
        return f"⚠️ Error al listar reuniones: {str(e)}"

def editar_reunion(data):
    try:
        id_reunion = data.get("id_reunion")
        nombre = data.get("nombre", "")
        fecha = parse_date(data.get("fecha", ""))
        hora_inicio = parse_time(data.get("hora_inicio", ""))
        hora_fin = parse_time(data.get("hora_fin", ""))

        if not id_reunion:
            return "⚠️ Debes proporcionar el ID de la reunión a editar."

        reunion = Reunion.objects.get(id=id_reunion)
        if nombre:
            reunion.nombre = nombre
        if fecha:
            reunion.fecha = fecha
        if hora_inicio:
            reunion.hora_inicio = hora_inicio
        if hora_fin:
            reunion.hora_fin = hora_fin
        reunion.save()

        return f"✏️ Reunión {id_reunion} actualizada."

    except Reunion.DoesNotExist:
        return "⚠️ No se encontró la reunión."

    except Exception as e:
        return f"⚠️ Error al editar la reunión: {str(e)}"

def eliminar_reunion(data):
    try:
        id_reunion = data.get("id_reunion")
        if not id_reunion:
            return "⚠️ Debes proporcionar el ID de la reunión a eliminar."

        reunion = Reunion.objects.get(id=id_reunion)
        reunion.delete()

        return f"🗑️ Reunión {id_reunion} eliminada con éxito."

    except Reunion.DoesNotExist:
        return "⚠️ No se encontró la reunión."

    except Exception as e:
        return f"⚠️ Error al eliminar la reunión: {str(e)}"