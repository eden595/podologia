from collections import Counter
from datetime import datetime, time, timedelta
import json
import re
import time as time_module
import unicodedata

import cloudinary
from cloudinary.utils import api_sign_request
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import PacienteForm, TratamientoForm
from .models import FotoTratamiento, Paciente, Tratamiento, borrar_archivo_storage_async

MAX_IMAGENES_POR_TRATAMIENTO = 10
MAX_IMAGEN_BYTES = 10 * 1024 * 1024
MAX_OTROS_CHARS = 1200
DIRECT_UPLOAD_FOLDERS = {
    'tratamiento_principal': 'media/tratamientos',
    'tratamiento_extra': 'media/tratamientos_extra',
}

PROCEDIMIENTOS_SELECCIONABLES = [
    'ONICOTOMIA',
    'DEBASTADO UNGUEAL',
    'RESECADO DE HIPERQUERATOSIS',
    'CURACION',
    'ESPICULECTOMIA',
    'ORTONIXIA',
    'LASER ONICOMICOSIS',
    'TECNICA FENOL ALCOHOL',
]
PROCEDIMIENTOS_PERMITIDOS = set(PROCEDIMIENTOS_SELECCIONABLES)
PROCEDIMIENTOS_ALIASES = {
    'ONICOTOMIA': 'ONICOTOMIA',
    'DEBASTADO': 'DEBASTADO UNGUEAL',
    'DEBASTADO DE LAMINA': 'DEBASTADO UNGUEAL',
    'DEBASTADO LAMINA': 'DEBASTADO UNGUEAL',
    'DEBASTADO UNGUEAL': 'DEBASTADO UNGUEAL',
    'DESBASTADO UNGUEAL': 'DEBASTADO UNGUEAL',
    'RESECADO DE HIPERQUERATOSIS': 'RESECADO DE HIPERQUERATOSIS',
    'RESECADO': 'RESECADO DE HIPERQUERATOSIS',
    'RESECADO DE HIPERQUERATOSIS SIN FIRMA': 'RESECADO DE HIPERQUERATOSIS',
    'CURACION': 'CURACION',
    'ESPICULECTOMIA': 'ESPICULECTOMIA',
    'DESPICULIZACION': 'ESPICULECTOMIA',
    'ORTONIXIA': 'ORTONIXIA',
    'LASER': 'LASER ONICOMICOSIS',
    'LASER ONICOMICOSIS': 'LASER ONICOMICOSIS',
    'TECNICA FENOL ALCOHOL': 'TECNICA FENOL ALCOHOL',
    'FENOL ALCOHOL': 'TECNICA FENOL ALCOHOL',
}


def _normalizar_texto(valor: str) -> str:
    valor = valor or ''
    try:
        valor = valor.encode('latin1').decode('utf-8')
    except UnicodeError:
        pass

    valor = unicodedata.normalize('NFKD', valor)
    valor = ''.join(ch for ch in valor if not unicodedata.combining(ch))
    valor = valor.upper()
    valor = re.sub(r'[^A-Z0-9 ]+', ' ', valor)
    return re.sub(r'\s+', ' ', valor).strip()


def _normalizar_etiqueta_procedimiento(valor: str) -> str:
    normalizado = _normalizar_texto(valor)
    if not normalizado:
        return ''
    return PROCEDIMIENTOS_ALIASES.get(normalizado, normalizado)


def _normalizar_procedimiento_registrado(texto: str) -> str:
    texto = (texto or '').strip()
    if not texto:
        return ''

    bloque_principal, separador, bloque_notas = texto.partition('|')
    items = [
        _normalizar_etiqueta_procedimiento(item)
        for item in bloque_principal.split(',')
        if item.strip()
    ]
    items_unicos = []
    for item in items:
        if item and item not in items_unicos:
            items_unicos.append(item)

    principal = ', '.join(items_unicos)
    notas = bloque_notas.strip()
    if separador and notas:
        if principal:
            return f'{principal} | {notas}'
        return notas
    return principal


def _descomponer_procedimiento_registrado(texto: str):
    texto = (texto or '').strip()
    if not texto:
        return [], ''

    bloque_principal, separador, bloque_notas = texto.partition('|')
    seleccionados = []
    restos = []

    for item in [item.strip() for item in bloque_principal.split(',') if item.strip()]:
        etiqueta = _normalizar_etiqueta_procedimiento(item)
        if etiqueta in PROCEDIMIENTOS_PERMITIDOS:
            if etiqueta not in seleccionados:
                seleccionados.append(etiqueta)
        else:
            restos.append(item)

    notas = bloque_notas.strip() if separador else ''
    if notas.upper().startswith('NOTAS:'):
        notas = notas.split(':', 1)[1].strip()

    if not separador and bloque_principal.strip().upper().startswith('NOTAS:'):
        notas = bloque_principal.split(':', 1)[1].strip()
        restos = []
        seleccionados = []

    if restos:
        notas = ' '.join(part for part in [', '.join(restos), notas] if part).strip()

    return seleccionados, notas


def _construir_procedimiento_registrado(seleccionados, otros):
    procedimiento_final = ', '.join(seleccionados)
    otros = (otros or '').strip()
    if otros:
        if procedimiento_final:
            return f'{procedimiento_final} | NOTAS: {otros}'
        return f'NOTAS: {otros}'
    return procedimiento_final


def _resumen_procedimiento_mostrable(texto: str):
    seleccionados, notas = _descomponer_procedimiento_registrado(texto)
    procedimiento = ', '.join(seleccionados)

    if procedimiento:
        return procedimiento, notas
    if notas:
        return 'Sin procedimiento catalogado', notas
    return 'Sin descripcion', ''


def _seleccionar_procedimientos_desde_post(request):
    seleccionados = []
    for item in [item.strip() for item in request.POST.getlist('tratamientos_check') if item.strip()]:
        etiqueta = _normalizar_etiqueta_procedimiento(item)
        if not etiqueta or etiqueta not in PROCEDIMIENTOS_PERMITIDOS:
            raise ValueError('Se detecto un procedimiento no permitido en el formulario.')
        if etiqueta not in seleccionados:
            seleccionados.append(etiqueta)
    return seleccionados


def _construir_fotos_edicion(tratamiento):
    fotos = []
    indice = 1

    if tratamiento.foto:
        fotos.append(
            {
                'url': tratamiento.foto.url,
                'label': f'Foto {indice}',
                'delete_url': reverse('eliminar_foto_principal', kwargs={'pk': tratamiento.pk}),
            }
        )
        indice += 1

    for foto in tratamiento.fotos_tratamiento.all().order_by('fecha_subida', 'id'):
        fotos.append(
            {
                'url': foto.imagen.url,
                'label': f'Foto {indice}',
                'delete_url': reverse('eliminar_foto_tratamiento', kwargs={'pk': foto.pk}),
            }
        )
        indice += 1

    return fotos


def _contexto_form_tratamiento(paciente, seleccionados=None, otros='', fecha=''):
    return {
        'paciente': paciente,
        'tratamientos_previos': seleccionados or [],
        'otros_previos': otros or '',
        'fecha_previo': fecha or '',
        'procedimientos_disponibles': PROCEDIMIENTOS_SELECCIONABLES,
        **_contexto_cloudinary_uploads(),
    }


def _usa_cloudinary_storage():
    try:
        backend = settings.STORAGES['default']['BACKEND']
    except Exception:
        return False
    return backend == 'cloudinary_storage.storage.MediaCloudinaryStorage'


def _contexto_cloudinary_uploads():
    return {
        'cloudinary_direct_uploads': _usa_cloudinary_storage(),
        'cloudinary_signature_url': reverse_lazy('cloudinary_upload_signature'),
    }


def _parse_direct_uploads(raw_value, upload_kind, *, multiple=True):
    if not raw_value:
        return [] if multiple else ''

    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError('No se pudo leer la respuesta de Cloudinary enviada por el navegador.') from exc

    if payload is None:
        return [] if multiple else ''

    if multiple:
        items = payload if isinstance(payload, list) else [payload]
    else:
        items = [payload]

    folder = DIRECT_UPLOAD_FOLDERS.get(upload_kind, '')
    resultados = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('El formato de una imagen subida no es valido.')

        public_id = str(item.get('public_id', '')).strip()
        resource_type = str(item.get('resource_type', 'image')).strip() or 'image'
        if not public_id or resource_type != 'image':
            raise ValueError('Cloudinary devolvio una imagen invalida para este formulario.')

        if folder and not public_id.startswith(f'{folder}/'):
            raise ValueError('Se detecto una carpeta de Cloudinary no permitida para la imagen subida.')

        resultados.append(public_id)

    if multiple:
        return resultados
    return resultados[0] if resultados else ''


def _agregar_errores_formulario(request, form):
    for field_name, errores in form.errors.items():
        if field_name == '__all__':
            etiqueta = 'Formulario'
        else:
            field = form.fields.get(field_name)
            etiqueta = (field.label if field else field_name).strip() or field_name

        for error in errores:
            messages.error(request, f'{etiqueta}: {error}')


def _inicio_dia_local(fecha_local):
    return timezone.make_aware(datetime.combine(fecha_local, time.min), timezone.get_current_timezone())


def _conteo_tratamientos_rango_fechas_local(fecha_inicio, fecha_fin_inclusiva):
    inicio_dt = _inicio_dia_local(fecha_inicio)
    fin_exclusivo_dt = _inicio_dia_local(fecha_fin_inclusiva + timedelta(days=1))
    return Tratamiento.objects.filter(fecha__gte=inicio_dt, fecha__lt=fin_exclusivo_dt).count()


def _conteo_tratamientos_dia_local(fecha_local):
    return _conteo_tratamientos_rango_fechas_local(fecha_local, fecha_local)


def health_check(request):
    return JsonResponse({'status': 'ok'})


class DashboardView(LoginRequiredMixin, ListView):
    model = Paciente
    template_name = 'pacientes/lista_pacientes.html'
    context_object_name = 'pacientes'
    paginate_by = 10
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        return super().get_queryset().order_by('-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        inicio_7_dias = hoy - timedelta(days=6)
        cache_key = f'dashboard_metrics:{hoy.isoformat()}'
        metrics = cache.get(cache_key)

        if metrics is None:
            conteo_procedimientos = Counter()
            procedimientos_registrados = Tratamiento.objects.values_list('procedimiento', flat=True)
            for procedimiento in procedimientos_registrados:
                seleccionados, _ = _descomponer_procedimiento_registrado(procedimiento)
                for item in seleccionados:
                    conteo_procedimientos[item] += 1

            procedimientos_ordenados = conteo_procedimientos.most_common()
            metrics = {
                'tratamientos_7_dias': _conteo_tratamientos_rango_fechas_local(inicio_7_dias, hoy),
                'tratamientos_chart_labels': [nombre for nombre, _ in procedimientos_ordenados],
                'tratamientos_chart_values': [cantidad for _, cantidad in procedimientos_ordenados],
            }
            cache.set(cache_key, metrics, 60)

        context['ultimos_pacientes'] = Paciente.objects.only('id', 'nombre', 'rut').order_by('-id')[:6]
        context['tratamientos_7_dias'] = metrics['tratamientos_7_dias']
        context['tratamientos_chart_labels'] = metrics['tratamientos_chart_labels']
        context['tratamientos_chart_values'] = metrics['tratamientos_chart_values']
        context['tratamientos_chart_total'] = sum(metrics['tratamientos_chart_values'])
        return context


class PacienteListView(LoginRequiredMixin, ListView):
    model = Paciente
    template_name = 'pacientes/administrar_pacientes.html'
    context_object_name = 'pacientes'
    paginate_by = 10
    http_method_names = ['get', 'head', 'options']

    def get_paginate_by(self, queryset):
        per_page = (self.request.GET.get('per_page') or '').strip()
        if per_page in {'10', '20', '50'}:
            return int(per_page)
        return self.paginate_by

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related(
            Prefetch(
                'tratamiento_set',
                queryset=Tratamiento.objects.order_by('-fecha'),
                to_attr='tratamientos_ordenados',
            )
        )
        termino = self.request.GET.get('buscar')

        if termino:
            termino_limpio = termino.strip()
            palabras = termino_limpio.split()
            query = Q()

            for palabra in palabras:
                query &= (Q(nombre__icontains=palabra) | Q(rut__icontains=palabra))

            queryset = queryset.filter(query).order_by('-id')
        else:
            queryset = queryset.order_by('-id')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        total_pacientes = Paciente.objects.count()
        en_tratamiento = Tratamiento.objects.values('paciente_id').distinct().count()
        per_page = (self.request.GET.get('per_page') or '').strip()

        pacientes_contexto = context.get('pacientes') or []
        for paciente in pacientes_contexto:
            total_procedimientos = 0
            for tratamiento in getattr(paciente, 'tratamientos_ordenados', []):
                seleccionados, _ = _descomponer_procedimiento_registrado(tratamiento.procedimiento)
                total_procedimientos += len(seleccionados)
            paciente.total_procedimientos_realizados = total_procedimientos

        context['buscar_actual'] = (self.request.GET.get('buscar') or '').strip()
        context['per_page_actual'] = per_page if per_page in {'10', '20', '50'} else str(self.paginate_by)

        context['total_pacientes'] = total_pacientes
        context['atenciones_hoy'] = _conteo_tratamientos_dia_local(hoy)
        context['en_tratamiento'] = en_tratamiento
        context['pacientes_sin_historial'] = max(total_pacientes - en_tratamiento, 0)
        return context


class PacienteCreateView(LoginRequiredMixin, CreateView):
    model = Paciente
    form_class = PacienteForm
    template_name = 'pacientes/formulario_paciente.html'
    success_url = reverse_lazy('lista_pacientes')
    http_method_names = ['get', 'post', 'head', 'options']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Paciente registrado correctamente.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'No se pudo guardar el paciente. Revisa los campos marcados.')
        _agregar_errores_formulario(self.request, form)
        return super().form_invalid(form)


class PacienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Paciente
    form_class = PacienteForm
    template_name = 'pacientes/formulario_paciente.html'
    success_url = reverse_lazy('lista_pacientes')
    http_method_names = ['get', 'post', 'head', 'options']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Paciente actualizado correctamente.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'No se pudo actualizar el paciente. Revisa los campos marcados.')
        _agregar_errores_formulario(self.request, form)
        return super().form_invalid(form)


class PacienteDeleteView(LoginRequiredMixin, DeleteView):
    model = Paciente
    template_name = 'pacientes/eliminar_paciente.html'
    success_url = reverse_lazy('lista_pacientes')
    http_method_names = ['get', 'post', 'head', 'options']

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        nombre = self.object.nombre
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Paciente "{nombre}" eliminado correctamente.')
        return response


@login_required
def detalle_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    historial = list(
        Tratamiento.objects.filter(paciente=paciente)
        .prefetch_related('fotos_tratamiento')
        .order_by('-fecha')
    )
    for item in historial:
        item.procedimiento_mostrable, item.notas_procedimiento = _resumen_procedimiento_mostrable(item.procedimiento)
        evidencias = []
        if item.foto:
            evidencias.append(
                {
                    'url': item.foto.url,
                    'label': 'Foto principal',
                }
            )

        for indice, foto in enumerate(item.fotos_tratamiento.all(), start=len(evidencias) + 1):
            evidencias.append(
                {
                    'url': foto.imagen.url,
                    'label': f'Foto {indice}',
                }
            )

        item.evidencias = evidencias
        item.total_evidencias = len(evidencias)

    try:
        fotos_galeria = paciente.fotos_galeria.all().order_by('-fecha_subida')
    except AttributeError:
        fotos_galeria = []

    return render(
        request,
        'pacientes/detalle_paciente.html',
        {
            'paciente': paciente,
            'historial': historial,
            'fotos_galeria': fotos_galeria,
        },
    )


@login_required
@require_http_methods(['POST'])
def cloudinary_upload_signature(request):
    if not _usa_cloudinary_storage():
        return JsonResponse({'detail': 'Cloudinary no esta habilitado en este entorno.'}, status=400)

    upload_kind = (request.POST.get('kind') or '').strip()
    folder = DIRECT_UPLOAD_FOLDERS.get(upload_kind)
    if not folder:
        return JsonResponse({'detail': 'Tipo de subida no permitido.'}, status=400)

    config = cloudinary.config()
    timestamp = int(time_module.time())
    params = {
        'folder': folder,
        'timestamp': timestamp,
        'unique_filename': 'true',
        'use_filename': 'true',
    }
    signature = api_sign_request(params, config.api_secret)

    return JsonResponse(
        {
            'api_key': config.api_key,
            'cloud_name': config.cloud_name,
            'folder': folder,
            'signature': signature,
            'timestamp': timestamp,
            'unique_filename': 'true',
            'upload_url': f'https://api.cloudinary.com/v1_1/{config.cloud_name}/image/upload',
            'use_filename': 'true',
        }
    )


@login_required
@require_http_methods(['GET', 'POST'])
def registrar_tratamiento(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)

    if request.method == 'POST':
        try:
            seleccionados = _seleccionar_procedimientos_desde_post(request)
        except ValueError as exc:
            messages.error(request, str(exc))
            return render(
                request,
                'pacientes/formulario_tratamiento.html',
                _contexto_form_tratamiento(paciente),
            )

        otros = request.POST.get('otros_texto', '').strip()
        fecha_input = request.POST.get('fecha', '').strip()
        firma_base64 = request.POST.get('firma_base64', '').strip()
        foto_principal_directa_raw = request.POST.get('foto_principal_directa', '').strip()
        fotos_extra_directas_raw = request.POST.get('fotos_extra_directas', '').strip()
        imagenes_extra = request.FILES.getlist('fotos_extra')
        contexto_form = _contexto_form_tratamiento(paciente, seleccionados, otros, fecha_input)

        try:
            foto_principal_directa = _parse_direct_uploads(
                foto_principal_directa_raw,
                'tratamiento_principal',
                multiple=False,
            )
            fotos_extra_directas = _parse_direct_uploads(
                fotos_extra_directas_raw,
                'tratamiento_extra',
                multiple=True,
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return render(request, 'pacientes/formulario_tratamiento.html', contexto_form)

        if foto_principal_directa or fotos_extra_directas:
            imagenes_extra = [item for item in [foto_principal_directa, *fotos_extra_directas] if item]

        if not seleccionados and not otros:
            messages.error(request, 'Debes seleccionar al menos un procedimiento o escribir una nota.')
            return render(request, 'pacientes/formulario_tratamiento.html', contexto_form)

        if len(otros) > MAX_OTROS_CHARS:
            messages.error(request, f'El campo "Notas" permite maximo {MAX_OTROS_CHARS} caracteres.')
            return render(request, 'pacientes/formulario_tratamiento.html', contexto_form)

        if not firma_base64 or not firma_base64.startswith('data:image/'):
            messages.error(request, 'La firma del paciente es obligatoria.')
            return render(request, 'pacientes/formulario_tratamiento.html', contexto_form)

        if len(imagenes_extra) > MAX_IMAGENES_POR_TRATAMIENTO:
            messages.error(request, f'Puedes subir un maximo de {MAX_IMAGENES_POR_TRATAMIENTO} imagenes por tratamiento.')
            return render(request, 'pacientes/formulario_tratamiento.html', contexto_form)

        for imagen in imagenes_extra:
            if isinstance(imagen, str):
                continue

            if not getattr(imagen, 'content_type', '').startswith('image/'):
                messages.error(request, f'El archivo "{imagen.name}" no es una imagen valida.')
                return render(request, 'pacientes/formulario_tratamiento.html', contexto_form)

            if imagen.size > MAX_IMAGEN_BYTES:
                messages.error(request, f'La imagen "{imagen.name}" supera el limite de 10 MB.')
                return render(request, 'pacientes/formulario_tratamiento.html', contexto_form)

        procedimiento_final = _construir_procedimiento_registrado(seleccionados, otros)

        fecha_final = timezone.now()
        if fecha_input:
            fecha_parseada = parse_datetime(fecha_input)
            if not fecha_parseada:
                messages.error(request, 'La fecha ingresada no es valida.')
                return render(request, 'pacientes/formulario_tratamiento.html', contexto_form)

            if timezone.is_naive(fecha_parseada):
                fecha_parseada = timezone.make_aware(fecha_parseada, timezone.get_current_timezone())

            if fecha_parseada > timezone.now() + timedelta(minutes=5):
                messages.error(request, 'La fecha no puede estar en el futuro.')
                return render(request, 'pacientes/formulario_tratamiento.html', contexto_form)

            fecha_final = fecha_parseada

        foto_principal = imagenes_extra[0] if imagenes_extra else None

        nuevo_tratamiento = Tratamiento.objects.create(
            paciente=paciente,
            fecha=fecha_final,
            procedimiento=procedimiento_final,
            foto=foto_principal,
            firma=firma_base64,
        )

        fotos_extra_para_guardar = imagenes_extra[1:] if foto_principal else []
        for img in fotos_extra_para_guardar:
            FotoTratamiento.objects.create(
                tratamiento=nuevo_tratamiento,
                imagen=img,
            )

        messages.success(request, 'Tratamiento registrado correctamente.')
        return redirect('detalle_paciente', pk=paciente.pk)

    return render(
        request,
        'pacientes/formulario_tratamiento.html',
        _contexto_form_tratamiento(paciente),
    )


class TratamientoUpdateView(LoginRequiredMixin, UpdateView):
    model = Tratamiento
    form_class = TratamientoForm
    template_name = 'pacientes/formulario_tratamiento_editar.html'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return super().get_queryset().prefetch_related('fotos_tratamiento')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method == 'POST':
            try:
                tratamientos_previos = _seleccionar_procedimientos_desde_post(self.request)
            except ValueError:
                tratamientos_previos = []
            otros_previos = self.request.POST.get('otros_texto', '').strip()
        else:
            tratamientos_previos, otros_previos = _descomponer_procedimiento_registrado(self.object.procedimiento)

        context.update(_contexto_cloudinary_uploads())
        context['procedimientos_disponibles'] = PROCEDIMIENTOS_SELECCIONABLES
        context['tratamientos_previos'] = tratamientos_previos
        context['otros_previos'] = otros_previos
        context['fotos_edicion'] = _construir_fotos_edicion(self.object)
        return context

    def form_valid(self, form):
        nuevas_fotos_directas_raw = self.request.POST.get('nuevas_fotos_extra_directas', '').strip()
        nuevas_imagenes = self.request.FILES.getlist('nuevas_fotos_extra')

        try:
            seleccionados = _seleccionar_procedimientos_desde_post(self.request)
        except ValueError as exc:
            form.add_error(None, str(exc))
            messages.error(self.request, 'No se pudieron guardar los cambios. Revisa los procedimientos seleccionados.')
            return self.form_invalid(form)

        otros = self.request.POST.get('otros_texto', '').strip()
        if not seleccionados and not otros:
            form.add_error(None, 'Debes seleccionar al menos un procedimiento o escribir una nota.')
            messages.error(self.request, 'No se pudieron guardar los cambios. Falta indicar el procedimiento realizado.')
            return self.form_invalid(form)

        if len(otros) > MAX_OTROS_CHARS:
            form.add_error(None, f'El campo "Notas" permite maximo {MAX_OTROS_CHARS} caracteres.')
            messages.error(self.request, 'No se pudieron guardar los cambios. Las notas son demasiado largas.')
            return self.form_invalid(form)

        try:
            nuevas_fotos_directas = _parse_direct_uploads(
                nuevas_fotos_directas_raw,
                'tratamiento_extra',
                multiple=True,
            )
        except ValueError as exc:
            form.add_error(None, str(exc))
            messages.error(self.request, 'No se pudieron guardar los cambios. La carga directa no fue valida.')
            return self.form_invalid(form)

        if nuevas_fotos_directas:
            nuevas_imagenes = nuevas_fotos_directas

        if len(nuevas_imagenes) > MAX_IMAGENES_POR_TRATAMIENTO:
            form.add_error(None, f'Puedes subir maximo {MAX_IMAGENES_POR_TRATAMIENTO} imagenes nuevas por edicion.')
            messages.error(self.request, 'No se pudieron guardar los cambios. Excediste el limite de imagenes.')
            return self.form_invalid(form)

        for imagen in nuevas_imagenes:
            if isinstance(imagen, str):
                continue

            if not getattr(imagen, 'content_type', '').startswith('image/'):
                form.add_error(None, f'El archivo "{imagen.name}" no es una imagen valida.')
                messages.error(self.request, 'No se pudieron guardar los cambios. Hay archivos invalidos.')
                return self.form_invalid(form)

            if imagen.size > MAX_IMAGEN_BYTES:
                form.add_error(None, f'La imagen "{imagen.name}" supera el limite de 10 MB.')
                messages.error(self.request, 'No se pudieron guardar los cambios. Hay imagenes demasiado grandes.')
                return self.form_invalid(form)

        nueva_firma = self.request.POST.get('firma_base64', '').strip()
        if nueva_firma and not nueva_firma.startswith('data:image/'):
            form.add_error(None, 'La firma enviada no tiene un formato valido.')
            messages.error(self.request, 'No se pudieron guardar los cambios. La firma no es valida.')
            return self.form_invalid(form)

        form.instance.procedimiento = _construir_procedimiento_registrado(seleccionados, otros)
        response = super().form_valid(form)
        tratamiento = self.object

        if nueva_firma:
            tratamiento.firma = nueva_firma
            tratamiento.save(update_fields=['firma'])

        for img in nuevas_imagenes:
            FotoTratamiento.objects.create(tratamiento=tratamiento, imagen=img)

        messages.success(self.request, 'Tratamiento actualizado correctamente.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'No se pudo actualizar el tratamiento. Revisa los errores del formulario.')
        _agregar_errores_formulario(self.request, form)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('detalle_paciente', kwargs={'pk': self.object.paciente.pk})


@login_required
@require_http_methods(['POST'])
def eliminar_foto_principal(request, pk):
    tratamiento = get_object_or_404(Tratamiento, pk=pk)
    if not tratamiento.foto:
        return JsonResponse({'detail': 'La foto ya no existe o fue eliminada.'}, status=404)

    nombre = tratamiento.foto.name
    storage = tratamiento.foto.storage
    tratamiento.foto = None
    tratamiento.save(update_fields=['foto'])
    borrar_archivo_storage_async(name=nombre, storage=storage)
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(['POST'])
def eliminar_foto_tratamiento(request, pk):
    foto = get_object_or_404(FotoTratamiento, pk=pk)
    foto.delete()
    return JsonResponse({'ok': True})


class TratamientoDeleteView(LoginRequiredMixin, DeleteView):
    model = Tratamiento
    template_name = 'pacientes/eliminar_historial.html'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_success_url(self):
        return reverse_lazy('detalle_paciente', kwargs={'pk': self.object.paciente.pk})

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        fecha = self.object.fecha.strftime('%d/%m/%Y %H:%M')
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Tratamiento del {fecha} eliminado correctamente.')
        return response
