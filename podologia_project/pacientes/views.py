from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError 
from .models import Paciente, Tratamiento, FotoGaleria # Importación corregida en una sola línea

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
            # 1. Guardamos el paciente en una variable 'nuevo_paciente' para usarlo después
            nuevo_paciente = Paciente.objects.create(
                nombre=request.POST.get('nombre'),
                rut=request.POST.get('rut'),
                telefono=request.POST.get('telefono'),
                email=request.POST.get('email'),
                diabetes=request.POST.get('diabetes') == 'on',
                hipertension=request.POST.get('hipertension') == 'on',
                alergias=request.POST.get('alergias', ''),
                observaciones_medicas=request.POST.get('observaciones_medicas', '')
            )

            # 2. LOGICA NUEVA: Guardar las múltiples fotos del historial
            imagenes = request.FILES.getlist('imagenes_extra') # Debe coincidir con el name del input HTML
            
            for img in imagenes:
                FotoGaleria.objects.create(
                    paciente=nuevo_paciente, 
                    imagen=img
                )

            return redirect('lista_pacientes')

        except IntegrityError:
            # Si el RUT ya existe, volvemos al formulario con un mensaje de error
            return render(request, 'pacientes/formulario_paciente.html', {
                'error': 'El RUT ingresado ya está registrado en el sistema.'
            })
            
    return render(request, 'pacientes/formulario_paciente.html')

@login_required
def detalle_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    historial = Tratamiento.objects.filter(paciente=paciente).order_by('-fecha')
    
    # También enviamos las fotos de la galería para que puedas verlas en el detalle (opcional por ahora)
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

        # Crear el tratamiento
        Tratamiento.objects.create(
            paciente=paciente,
            procedimiento=procedimiento_final,
            foto=request.FILES.get('foto'), 
            firma=request.POST.get('firma_base64')
        )
        return redirect('detalle_paciente', pk=paciente.pk)
        
    return render(request, 'pacientes/formulario_tratamiento.html', {'paciente': paciente})