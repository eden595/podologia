import re
from datetime import timedelta

from django import forms
from django.utils import timezone

from .models import Paciente, Tratamiento

STANDARD_RUT_REGEX = re.compile(r"^\d{7,8}-[\dkK]$")
PHONE_REGEX = re.compile(r"^[0-9+()\-\s]{8,20}$")


def _normalizar_espacios(valor: str) -> str:
    return " ".join((valor or "").split())


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
            'rut': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 12.345.678-9, Pasaporte o RUT provisorio'}),
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
        raw_rut = (self.cleaned_data.get('rut') or '').strip().upper()
        # Eliminar caracteres no permitidos en documentos
        limpio = re.sub(r'[^A-Z0-9\-\.]', '', raw_rut)

        if not limpio or len(limpio) < 3:
            raise forms.ValidationError('Ingresa un RUT, DNI o Pasaporte valido (minimo 3 caracteres).')

        if len(limpio) > 15:
            raise forms.ValidationError('El documento no puede superar los 15 caracteres.')

        # Intentar formatear como RUT chileno tradicional si solo contiene digitos y/o K
        solo_numeros_k = re.sub(r'[^0-9K]', '', limpio)
        if 8 <= len(solo_numeros_k) <= 9:
            cuerpo = solo_numeros_k[:-1]
            dv = solo_numeros_k[-1]
            dv_esperado = _digito_verificador_rut(cuerpo)
            if dv == dv_esperado:
                cuerpo_puntos = f"{int(cuerpo):,}".replace(",", ".")
                return f"{cuerpo_puntos}-{dv}"


        return limpio


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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha'].required = False

    class Meta:
        model = Tratamiento
        fields = ['fecha']
        widgets = {
            'fecha': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if not fecha and self.instance and self.instance.pk:
            return self.instance.fecha
        if fecha and fecha > timezone.now() + timedelta(minutes=5):
            raise forms.ValidationError('La fecha no puede estar en el futuro.')
        return fecha
