import re
from datetime import timedelta

from django import forms
from django.utils import timezone

from .models import Paciente, Tratamiento

RUT_REGEX = re.compile(r"^\d{7,8}-[\dkK]$")
PHONE_REGEX = re.compile(r"^[0-9+()\-\s]{8,20}$")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _normalizar_espacios(valor: str) -> str:
    return " ".join((valor or "").split())


def _normalizar_rut(valor: str) -> str:
    bruto = re.sub(r"[^0-9kK]", "", (valor or ""))
    if len(bruto) < 8:
        return bruto
    cuerpo, dv = bruto[:-1], bruto[-1].upper()
    return f"{cuerpo}-{dv}"


def _digito_verificador_rut(cuerpo: str) -> str:
    serie = [2, 3, 4, 5, 6, 7]
    suma = 0
    idx = 0
    for digito in reversed(cuerpo):
        suma += int(digito) * serie[idx]
        idx = (idx + 1) % len(serie)
    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = '__all__'
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre completo'}),
            'rut': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: [REDACTED_DB_PASSWORD]-9'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Calle, Número, Comuna'}),
            'alergias': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'observaciones_medicas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_nombre(self):
        nombre = _normalizar_espacios(self.cleaned_data.get('nombre', ''))
        if len(nombre) < 3:
            raise forms.ValidationError('Ingresa un nombre valido (minimo 3 caracteres).')
        return nombre

    def clean_rut(self):
        rut = _normalizar_rut(self.cleaned_data.get('rut', ''))
        if not RUT_REGEX.fullmatch(rut):
            raise forms.ValidationError('Formato de RUT invalido. Usa [REDACTED_DB_PASSWORD]-9 o [REDACTED_DB_PASSWORD]-K.')

        cuerpo, dv = rut.split('-')
        dv_esperado = _digito_verificador_rut(cuerpo)
        if dv.upper() != dv_esperado:
            raise forms.ValidationError('RUT invalido: digito verificador incorrecto.')

        return rut.upper()

    def clean_telefono(self):
        telefono = _normalizar_espacios(self.cleaned_data.get('telefono', ''))
        if telefono and not PHONE_REGEX.fullmatch(telefono):
            raise forms.ValidationError('Telefono invalido. Usa solo numeros y simbolos + ( ) -.')
        return telefono

    def clean_direccion(self):
        direccion = _normalizar_espacios(self.cleaned_data.get('direccion', ''))
        if direccion and len(direccion) < 5:
            raise forms.ValidationError('Direccion demasiado corta.')
        return direccion

    def clean_alergias(self):
        return (self.cleaned_data.get('alergias') or '').strip()

    def clean_observaciones_medicas(self):
        return (self.cleaned_data.get('observaciones_medicas') or '').strip()


class TratamientoForm(forms.ModelForm):
    class Meta:
        model = Tratamiento
        # Solo editamos el texto y la foto principal al actualizar
        fields = ['fecha', 'procedimiento', 'foto']
        widgets = {
            'fecha': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'procedimiento': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if fecha and fecha > timezone.now() + timedelta(minutes=5):
            raise forms.ValidationError('La fecha no puede estar en el futuro.')
        return fecha

    def clean_procedimiento(self):
        procedimiento = (self.cleaned_data.get('procedimiento') or '').strip()
        if len(procedimiento) < 3:
            raise forms.ValidationError('La descripcion del tratamiento es obligatoria.')
        return procedimiento

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        if not foto:
            return foto

        if foto.size > MAX_UPLOAD_BYTES:
            raise forms.ValidationError('La foto principal supera el limite de 10 MB.')

        if not getattr(foto, 'content_type', '').startswith('image/'):
            raise forms.ValidationError('Solo se permiten imagenes en la foto principal.')

        return foto
