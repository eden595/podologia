from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from .models import Paciente, Tratamiento
from django.contrib.auth.decorators import login_required # IMPORTANTE

@login_required
def lista_pacientes(request):
    termino = request.GET.get('buscar', '')
    if termino:
        pacientes = Paciente.objects.filter(Q(nombre__icontains=termino) | Q(rut__icontains=termino)).order_by('-id')
    else:
        pacientes = Paciente.objects.all().order_by('-id')
    return render(request, 'pacientes/lista_pacientes.html', {'pacientes': pacientes, 'termino_busqueda': termino})

@login_required
def crear_paciente(request):
    if request.method == "POST":
        Paciente.objects.create(
            nombre=request.POST.get('nombre'),
            rut=request.POST.get('rut'),
            telefono=request.POST.get('telefono'), # CAPTURA DEL TELÉFONO
            email=request.POST.get('email'),
            diabetes=request.POST.get('diabetes') == 'on',
            hipertension=request.POST.get('hipertension') == 'on',
            alergias=request.POST.get('alergias', ''),
            observaciones_medicas=request.POST.get('observaciones_medicas', '')
        )
        return redirect('lista_pacientes')
    return render(request, 'pacientes/formulario_paciente.html')

@login_required
def detalle_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    historial = Tratamiento.objects.filter(paciente=paciente).order_by('-fecha')
    return render(request, 'pacientes/detalle_paciente.html', {'paciente': paciente, 'historial': historial})

@login_required
def registrar_tratamiento(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    if request.method == "POST":
        seleccionados = request.POST.getlist('tratamientos_check')
        otros = request.POST.get('otros_texto', '')
        procedimiento_final = ", ".join(seleccionados)
        if otros: procedimiento_final += f" | Notas: {otros}"

        Tratamiento.objects.create(
            paciente=paciente,
            procedimiento=procedimiento_final,
            foto=request.FILES.get('foto'),
            firma=request.POST.get('firma_base64')
        )
        return redirect('detalle_paciente', pk=paciente.pk)
    return render(request, 'pacientes/formulario_tratamiento.html', {'paciente': paciente})