from django.urls import path

from . import views

urlpatterns = [
    path('healthz/', views.health_check, name='health_check'),
    path('healthz/db/', views.health_check_db, name='health_check_db'),
    path('', views.DashboardView.as_view(), name='lista_pacientes'),
    path('pacientes/administrar/', views.PacienteListView.as_view(), name='administrar_pacientes'),
    path('paciente/nuevo/', views.PacienteCreateView.as_view(), name='crear_paciente'),
    path('paciente/detalle/<int:pk>/', views.detalle_paciente, name='detalle_paciente'),
    path('paciente/editar/<int:pk>/', views.PacienteUpdateView.as_view(), name='editar_paciente'),
    path('paciente/eliminar/<int:pk>/', views.PacienteDeleteView.as_view(), name='eliminar_paciente'),
    path('api/cloudinary/signature/', views.cloudinary_upload_signature, name='cloudinary_upload_signature'),
    path('tratamiento/nuevo/<int:pk>/', views.registrar_tratamiento, name='registrar_tratamiento'),
    path('tratamiento/editar/<int:pk>/', views.TratamientoUpdateView.as_view(), name='editar_historial'),
    path('tratamiento/<int:pk>/foto-principal/eliminar/', views.eliminar_foto_principal, name='eliminar_foto_principal'),
    path('tratamiento/foto/<int:pk>/eliminar/', views.eliminar_foto_tratamiento, name='eliminar_foto_tratamiento'),
    path('tratamiento/eliminar/<int:pk>/', views.TratamientoDeleteView.as_view(), name='eliminar_historial'),
]
