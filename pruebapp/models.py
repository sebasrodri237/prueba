from django.db import models

class Reunion(models.Model):
    nombre = models.CharField(max_length=200)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

