from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_pacientes, name='lista_pacientes'),
    path('nuevo/', views.crear_paciente, name='crear_paciente'),
    path('paciente/<int:pk>/', views.detalle_paciente, name='detalle_paciente'),
    path('paciente/<int:pk>/nuevo-tratamiento/', views.registrar_tratamiento, name='registrar_tratamiento'),
    
]