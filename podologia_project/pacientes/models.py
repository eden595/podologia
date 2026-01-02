from django.db import models
from django.utils import timezone
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
import os # Necesario para borrar archivos
from django.db.models.signals import post_delete # Necesario para la señal de borrado
from django.dispatch import receiver # Necesario para recibir la señal

# --- FUNCIÓN PARA COMPRIMIR FOTOS ---
def comprimir_imagen(image_field, quality=60):
    img = Image.open(image_field)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    max_width = 1280
    if img.width > max_width:
        output_size = (max_width, int(max_width * img.height / img.width))
        img.thumbnail(output_size)
    output = BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True)
    output.seek(0)
    return InMemoryUploadedFile(
        output, 
        'ImageField', 
        "%s.jpg" % image_field.name.split('.')[0], 
        'image/jpeg', 
        sys.getsizeof(output), 
        None
    )

# ==========================================
#                 MODELOS
# ==========================================

class Paciente(models.Model):
    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=15, unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    
    # Ficha Técnica
    diabetes = models.BooleanField(default=False)
    hipertension = models.BooleanField(default=False)
    alergias = models.TextField(blank=True, null=True, help_text="Ej: Penicilina")
    observaciones_medicas = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Tratamiento(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    fecha = models.DateTimeField(default=timezone.now)
    procedimiento = models.TextField()
    foto = models.ImageField(upload_to='tratamientos/', null=True, blank=True)
    firma = models.TextField() 

    def save(self, *args, **kwargs):
        if self.foto and not self.foto._committed:
            self.foto = comprimir_imagen(self.foto)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.paciente.nombre} - {self.fecha.strftime('%d/%m/%Y')}"

class FotoGaleria(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='fotos_galeria')
    imagen = models.ImageField(upload_to='historial_medico/')
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.imagen and not self.imagen._committed:
            self.imagen = comprimir_imagen(self.imagen)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Foto de {self.paciente.nombre} - {self.fecha_subida}"
    
class FotoTratamiento(models.Model):
    tratamiento = models.ForeignKey(Tratamiento, on_delete=models.CASCADE, related_name='fotos_tratamiento')
    imagen = models.ImageField(upload_to='tratamientos_extra/')
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.imagen and not self.imagen._committed:
            self.imagen = comprimir_imagen(self.imagen)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Foto extra del tratamiento {self.tratamiento.id}"

# ==========================================
#        SEÑALES DE BORRADO AUTOMÁTICO
# ==========================================
# Esto hace que cuando borres en la web, se borre el archivo del disco

@receiver(post_delete, sender=Tratamiento)
def borrar_foto_tratamiento(sender, instance, **kwargs):
    """ Borra la foto principal del tratamiento """
    if instance.foto:
        if os.path.isfile(instance.foto.path):
            os.remove(instance.foto.path)

@receiver(post_delete, sender=FotoGaleria)
def borrar_foto_galeria(sender, instance, **kwargs):
    """ Borra la foto de la galería """
    if instance.imagen:
        if os.path.isfile(instance.imagen.path):
            os.remove(instance.imagen.path)

@receiver(post_delete, sender=FotoTratamiento)
def borrar_foto_extra(sender, instance, **kwargs):
    """ Borra las fotos extra del tratamiento """
    if instance.imagen:
        if os.path.isfile(instance.imagen.path):
            os.remove(instance.imagen.path)