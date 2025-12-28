from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # Sistema de autenticación (login/logout)
    path('accounts/', include('django.contrib.auth.urls')), 
    # Rutas de la aplicación principal
    path('', include('pacientes.urls')), 
]

# Configuración para servir archivos multimedia (fotos) en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)