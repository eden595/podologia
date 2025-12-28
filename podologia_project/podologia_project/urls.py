from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Esta línea es la que hace que funcione el login/logout de Django
    path('accounts/', include('django.contrib.auth.urls')), 
    # Esta es tu app de pacientes (asegúrate que el nombre sea correcto)
    path('', include('pacientes.urls')), 
]