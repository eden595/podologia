from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db import IntegrityError

# Asegúrate de importar tus modelos y formularios correctamente
from .models import Paciente, Tratamiento, FotoTratamiento
from .forms import PacienteForm, HistorialForm 
# Nota: Asumo que en forms.py llamaste a la clase 'HistorialForm' aunque el modelo sea 'Tratamiento'.
# Si cambiaste el nombre en forms.py a 'TratamientoForm', actualiza la importación arriba.

# ==========================================
#              GESTIÓN DE PACIENTES
# ==========================================

# 1. LISTAR PACIENTES (Con tu buscador integrado)
class PacienteListView(LoginRequiredMixin, ListView):
    model = Paciente
    template_name = 'pacientes/lista_pacientes.html'
    context_object_name = 'pacientes'
    paginate_by = 10  # Opcional: paginación

    def get_queryset(self):
        # Recuperamos el queryset original
        queryset = super().get_queryset()
        # Obtenemos el término de búsqueda de la URL
        termino = self.request.GET.get('buscar')
        
        if termino:
            # Filtramos por nombre O rut (tu lógica original)
            queryset = queryset.filter(
                Q(nombre__icontains=termino) | 
                Q(rut__icontains=termino)
            ).order_by('-id')
        else:
            queryset = queryset.order_by('-id')
        return queryset

    def get_context_data(self, **kwargs):
        # Pasamos el término al template para que se mantenga en la cajita de búsqueda
        context = super().get_context_data(**kwargs)
        context['termino_busqueda'] = self.request.GET.get('buscar', '')
        return context

# 2. CREAR PACIENTE
class PacienteCreateView(LoginRequiredMixin, CreateView):
    model = Paciente
    form_class = PacienteForm
    template_name = 'pacientes/formulario_paciente.html'
    success_url = reverse_lazy('lista_pacientes')

    def form_invalid(self, form):
        # Si hay error (ej. RUT duplicado), Django lo maneja, 
        # pero si quieres pasar un mensaje custom de IntegrityError manual:
        return super().form_invalid(form)

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

# 5. DETALLE PACIENTE (Ficha completa)
# Mantenemos esto como función porque obtienes mucha info distinta (historial, fotos, etc.)
@login_required
def detalle_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    # Aquí usamos 'Tratamiento' como en tu código original
    historial = Tratamiento.objects.filter(paciente=paciente).order_by('-fecha')
    
    # Manejo de errores por si no tienes el modelo FotoGaleria migrado aún
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

# 6. CREAR TRATAMIENTO (Mantenemos tu función original compleja)
# Usamos función porque manejas request.FILES y lógica de checkbox manual
@login_required
def registrar_tratamiento(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    
    if request.method == "POST":
        seleccionados = request.POST.getlist('tratamientos_check')
        otros = request.POST.get('otros_texto', '')
        
        # Unir lista de procedimientos
        procedimiento_final = ", ".join(seleccionados)
        if otros: 
            procedimiento_final += f" | Notas: {otros}"

        # Crear el tratamiento 
        nuevo_tratamiento = Tratamiento.objects.create(
            paciente=paciente,
            procedimiento=procedimiento_final, # Asegúrate que tu modelo tenga este campo o adapta el form
            # Nota: Si usas HistorialForm para editar, este campo 'procedimiento' debe existir en el modelo
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

# 7. EDITAR TRATAMIENTO (Nueva funcionalidad solicitada)
class TratamientoUpdateView(LoginRequiredMixin, UpdateView):
    model = Tratamiento
    form_class = HistorialForm # Usamos el form que creamos en el paso anterior
    template_name = 'pacientes/formulario_tratamiento_editar.html' # Nuevo template simple
    
    def get_success_url(self):
        # Al guardar, volvemos a la ficha del paciente
        return reverse_lazy('detalle_paciente', kwargs={'pk': self.object.paciente.pk})

# 8. ELIMINAR TRATAMIENTO (Nueva funcionalidad solicitada)
class TratamientoDeleteView(LoginRequiredMixin, DeleteView):
    model = Tratamiento
    template_name = 'pacientes/eliminar_historial.html'
    
    def get_success_url(self):
        return reverse_lazy('detalle_paciente', kwargs={'pk': self.object.paciente.pk})