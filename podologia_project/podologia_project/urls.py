from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views # Importamos vistas de auth

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- BLOQUEO DE LOGIN ---
    # Si alguien intenta entrar a 'login' y ya está autenticado, lo manda a la lista.
    path('accounts/login/', auth_views.LoginView.as_view(redirect_authenticated_user=True), name='login'),
    
    # Incluimos el resto de las URLs de autenticación (logout, password reset, etc.)
    path('accounts/', include('django.contrib.auth.urls')), 
    
    # Rutas de la aplicación principal
    path('', include('pacientes.urls')), 
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)