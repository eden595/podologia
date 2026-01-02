from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Paciente, Tratamiento, FotoTratamiento
from .forms import PacienteForm, TratamientoForm 

# ==========================================
#              GESTIÓN DE PACIENTES
# ==========================================

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

class PacienteCreateView(LoginRequiredMixin, CreateView):
    model = Paciente
    form_class = PacienteForm
    template_name = 'pacientes/formulario_paciente.html'
    success_url = reverse_lazy('lista_pacientes')

class PacienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Paciente
    form_class = PacienteForm
    template_name = 'pacientes/formulario_paciente.html'
    success_url = reverse_lazy('lista_pacientes')

class PacienteDeleteView(LoginRequiredMixin, DeleteView):
    model = Paciente
    template_name = 'pacientes/eliminar_paciente.html'
    success_url = reverse_lazy('lista_pacientes')

@login_required
def detalle_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    historial = Tratamiento.objects.filter(paciente=paciente).order_by('-fecha')
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

@login_required
def registrar_tratamiento(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    
    if request.method == "POST":
        seleccionados = request.POST.getlist('tratamientos_check')
        otros = request.POST.get('otros_texto', '')
        
        procedimiento_final = ", ".join(seleccionados)
        if otros: 
            if procedimiento_final:
                procedimiento_final += f" | Notas: {otros}"
            else:
                procedimiento_final = f"Notas: {otros}"

        # Crear Tratamiento
        nuevo_tratamiento = Tratamiento.objects.create(
            paciente=paciente,
            procedimiento=procedimiento_final,
            # Guardamos la primera foto como principal si existe
            foto=request.FILES.getlist('fotos_extra')[0] if request.FILES.getlist('fotos_extra') else None, 
            firma=request.POST.get('firma_base64')
        )

        # Guardar fotos EXTRA (Todas)
        imagenes_extra = request.FILES.getlist('fotos_extra')
        for img in imagenes_extra:
            FotoTratamiento.objects.create(
                tratamiento=nuevo_tratamiento,
                imagen=img
            )

        return redirect('detalle_paciente', pk=paciente.pk)
        
    return render(request, 'pacientes/formulario_tratamiento.html', {'paciente': paciente})

class TratamientoUpdateView(LoginRequiredMixin, UpdateView):
    model = Tratamiento
    form_class = TratamientoForm
    template_name = 'pacientes/formulario_tratamiento_editar.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        tratamiento = self.object

        # 1. ACTUALIZAR FIRMA (Si se modificó)
        nueva_firma = self.request.POST.get('firma_base64')
        if nueva_firma and "data:image" in nueva_firma:
            tratamiento.firma = nueva_firma
            tratamiento.save()

        # 2. AGREGAR FOTOS NUEVAS
        nuevas_imagenes = self.request.FILES.getlist('nuevas_fotos_extra')
        for img in nuevas_imagenes:
            FotoTratamiento.objects.create(tratamiento=tratamiento, imagen=img)

        # 3. BORRAR FOTOS MARCADAS
        for key in self.request.POST:
            if key.startswith('borrar_foto_'):
                foto_id = key.split('_')[2] 
                try:
                    foto = FotoTratamiento.objects.get(id=foto_id, tratamiento=tratamiento)
                    foto.delete()
                except (FotoTratamiento.DoesNotExist, ValueError):
                    pass

        return response

    def get_success_url(self):
        return reverse_lazy('detalle_paciente', kwargs={'pk': self.object.paciente.pk})

class TratamientoDeleteView(LoginRequiredMixin, DeleteView):
    model = Tratamiento
    template_name = 'pacientes/eliminar_historial.html'
    
    def get_success_url(self):
        return reverse_lazy('detalle_paciente', kwargs={'pk': self.object.paciente.pk})