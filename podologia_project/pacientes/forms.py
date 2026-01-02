from django import forms
from .models import Paciente, Tratamiento

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