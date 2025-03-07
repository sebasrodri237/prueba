from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db.models import Q
from .models import Reunion
from .serializers import ReunionSerializer

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
