from django import forms
from .models import Paciente, HistorialClinico

class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = '__all__' # O haz una lista: ['nombre', 'edad', 'telefono']
        # Puedes agregar widgets para que se vean mejor con tu CSS actual
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

class HistorialForm(forms.ModelForm):
    class Meta:
        model = HistorialClinico
        fields = '__all__'
        widgets = {
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }