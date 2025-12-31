from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError 
from .models import Paciente, Tratamiento, FotoTratamiento, FotoGaleria

@login_required
def lista_pacientes(request):
    termino = request.GET.get('buscar', '')
    if termino:
        pacientes = Paciente.objects.filter(
            Q(nombre__icontains=termino) | Q(rut__icontains=termino)
        ).order_by('-id')
    else:
        pacientes = Paciente.objects.all().order_by('-id')
    return render(request, 'pacientes/lista_pacientes.html', {'pacientes': pacientes, 'termino_busqueda': termino})

@login_required
def crear_paciente(request):
    if request.method == "POST":
        try:
            # Solo guardamos los datos del paciente, sin fotos
            Paciente.objects.create(
                nombre=request.POST.get('nombre'),
                rut=request.POST.get('rut'),
                telefono=request.POST.get('telefono'),
                email=request.POST.get('email'),
                diabetes=request.POST.get('diabetes') == 'on',
                hipertension=request.POST.get('hipertension') == 'on',
                alergias=request.POST.get('alergias', ''),
                observaciones_medicas=request.POST.get('observaciones_medicas', '')
            )
            return redirect('lista_pacientes')

        except IntegrityError:
            return render(request, 'pacientes/formulario_paciente.html', {
                'error': 'El RUT ingresado ya está registrado en el sistema.'
            })
            
    return render(request, 'pacientes/formulario_paciente.html')

@login_required
def detalle_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    historial = Tratamiento.objects.filter(paciente=paciente).order_by('-fecha')
    
    # Mantenemos esto por si en el futuro quieres agregar fotos, no da error dejarlo
    fotos_galeria = paciente.fotos_galeria.all().order_by('-fecha_subida')

    return render(request, 'pacientes/detalle_paciente.html', {
        'paciente': paciente, 
        'historial': historial,
        'fotos_galeria': fotos_galeria
    })

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

        # 1. Crear el tratamiento 
        nuevo_tratamiento = Tratamiento.objects.create(
            paciente=paciente,
            procedimiento=procedimiento_final,
            # (Opcional) Guardamos la primera foto en el campo antiguo por compatibilidad
            foto=request.FILES.getlist('fotos_extra')[0] if request.FILES.getlist('fotos_extra') else None, 
            firma=request.POST.get('firma_base64')
        )

        # 2. Guardar fotos EXTRA del tratamiento
        imagenes_extra = request.FILES.getlist('fotos_extra')
        
        for img in imagenes_extra:
            FotoTratamiento.objects.create(
                tratamiento=nuevo_tratamiento,
                imagen=img
            )

        return redirect('detalle_paciente', pk=paciente.pk)
        
    return render(request, 'pacientes/formulario_tratamiento.html', {'paciente': paciente})