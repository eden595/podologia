from django.db import models

class Paciente(models.Model):
    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=15, unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True) # NUEVO CAMPO
    email = models.EmailField()
    # Ficha Técnica
    diabetes = models.BooleanField(default=False)
    hipertension = models.BooleanField(default=False)
    alergias = models.TextField(blank=True, null=True, help_text="Ej: Penicilina")
    observaciones_medicas = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Tratamiento(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    procedimiento = models.TextField()
    foto = models.ImageField(upload_to='tratamientos/', null=True, blank=True)
    firma = models.TextField() 

    def __str__(self):
        return f"{self.paciente.nombre} - {self.fecha.strftime('%d/%m/%Y')}"