from django.contrib import admin
from .models import Paciente, Tratamiento

admin.site.register(Paciente)
admin.site.register(Tratamiento)