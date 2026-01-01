from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db import IntegrityError

# Importamos los modelos CORRECTOS según tu models.py
from .models import Paciente, Tratamiento, FotoTratamiento
# Importamos los formularios corregidos
from .forms import PacienteForm, TratamientoForm 

# ==========================================
#              GESTIÓN DE PACIENTES
# ==========================================

# 1. LISTAR PACIENTES (Buscador integrado)
class PacienteListView(LoginRequiredMixin, ListView):
    model = Paciente
    template_name = 'pacientes/lista_pacientes.html'
    context_object_name = 'pacientes'
    paginate_by = 10 

    def get_queryset(self):
        queryset = super().get_queryset()
        termino = self.request.GET.get('buscar')
        
        if termino:
            queryset = queryset.filter(
                Q(nombre__icontains=termino) | 
                Q(rut__icontains=termino)
            ).order_by('-id')
        else:
            queryset = queryset.order_by('-id')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['termino_busqueda'] = self.request.GET.get('buscar', '')
        return context

# 2. CREAR PACIENTE
class PacienteCreateView(LoginRequiredMixin, CreateView):
    model = Paciente
    form_class = PacienteForm
    template_name = 'pacientes/formulario_paciente.html'
    success_url = reverse_lazy('lista_pacientes')

# 3. ACTUALIZAR PACIENTE
class PacienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Paciente
    form_class = PacienteForm
    template_name = 'pacientes/formulario_paciente.html'
    success_url = reverse_lazy('lista_pacientes')

# 4. ELIMINAR PACIENTE
class PacienteDeleteView(LoginRequiredMixin, DeleteView):
    model = Paciente
    template_name = 'pacientes/eliminar_paciente.html'
    success_url = reverse_lazy('lista_pacientes')

# 5. DETALLE PACIENTE (La Ficha que te daba error)
@login_required
def detalle_paciente(request, pk):
    # Buscamos al paciente
    paciente = get_object_or_404(Paciente, pk=pk)
    
    # Buscamos los TRATAMIENTOS (antes llamado Historial)
    # El related_name no está definido en models, así que usamos _set o filtro directo
    historial = Tratamiento.objects.filter(paciente=paciente).order_by('-fecha')
    
    # Buscamos las fotos de galería (try/except por si acaso)
    try:
        fotos_galeria = paciente.fotos_galeria.all().order_by('-fecha_subida')
    except AttributeError:
        fotos_galeria = []

    return render(request, 'pacientes/detalle_paciente.html', {
        'paciente': paciente, 
        'historial': historial,
        'fotos_galeria': fotos_galeria
    })


# ==========================================
#           GESTIÓN DE TRATAMIENTOS
# ==========================================

# 6. CREAR TRATAMIENTO (Tu función personalizada con firma y fotos extra)
@login_required
def registrar_tratamiento(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    
    if request.method == "POST":
        seleccionados = request.POST.getlist('tratamientos_check')
        otros = request.POST.get('otros_texto', '')
        
        procedimiento_final = ", ".join(seleccionados)
        if otros: 
            procedimiento_final += f" | Notas: {otros}"

        # Crear el Objeto Tratamiento
        nuevo_tratamiento = Tratamiento.objects.create(
            paciente=paciente,
            procedimiento=procedimiento_final,
            foto=request.FILES.getlist('fotos_extra')[0] if request.FILES.getlist('fotos_extra') else None, 
            firma=request.POST.get('firma_base64')
        )

        # Guardar fotos EXTRA
        imagenes_extra = request.FILES.getlist('fotos_extra')
        for img in imagenes_extra:
            FotoTratamiento.objects.create(
                tratamiento=nuevo_tratamiento,
                imagen=img
            )

        return redirect('detalle_paciente', pk=paciente.pk)
        
    return render(request, 'pacientes/formulario_tratamiento.html', {'paciente': paciente})

# 7. EDITAR TRATAMIENTO (Corrección: Usamos Tratamiento y TratamientoForm)
class TratamientoUpdateView(LoginRequiredMixin, UpdateView):
    model = Tratamiento
    form_class = TratamientoForm # <--- Formulario corregido
    template_name = 'pacientes/formulario_tratamiento_editar.html'
    
    def get_success_url(self):
        return reverse_lazy('detalle_paciente', kwargs={'pk': self.object.paciente.pk})

# 8. ELIMINAR TRATAMIENTO (Corrección: Usamos Tratamiento)
class TratamientoDeleteView(LoginRequiredMixin, DeleteView):
    model = Tratamiento
    template_name = 'pacientes/eliminar_historial.html'
    
    def get_success_url(self):
        return reverse_lazy('detalle_paciente', kwargs={'pk': self.object.paciente.pk})