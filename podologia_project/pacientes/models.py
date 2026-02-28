from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

from PIL import Image, ImageOps
from django.core.files.storage import storages
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone

DELETE_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def comprimir_imagen(image_field, quality=90):
    try:
        img = Image.open(image_field)

        img = ImageOps.exif_transpose(img)

        if img.mode != 'RGB':
            img = img.convert('RGB')

        max_width = 1920
        if img.width > max_width:
            output_size = (max_width, int(max_width * img.height / img.width))
            img.thumbnail(output_size, Image.Resampling.LANCZOS)

        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)

        return InMemoryUploadedFile(
            output,
            'ImageField',
            f"{image_field.name.split('.')[0]}.jpg",
            'image/jpeg',
            output.getbuffer().nbytes,
            None,
        )
    except Exception as exc:
        print(f"Error al comprimir imagen: {exc}")
        return image_field


def borrar_archivo_storage_async(field_file=None, *, name='', storage=None):
    nombre = name or getattr(field_file, 'name', '') or ''
    storage = storage or getattr(field_file, 'storage', None) or storages['default']

    if not nombre:
        return

    def _delete():
        try:
            storage.delete(nombre)
        except Exception as exc:
            print(f"Error al borrar archivo '{nombre}': {exc}")

    try:
        transaction.on_commit(lambda: DELETE_EXECUTOR.submit(_delete))
    except RuntimeError:
        DELETE_EXECUTOR.submit(_delete)


class Paciente(models.Model):
    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=15, unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)

    diabetes = models.BooleanField(default=False)
    hipertension = models.BooleanField(default=False)
    alergias = models.TextField(blank=True, null=True, help_text='Ej: Penicilina')
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
        return f'{self.paciente.nombre} - {self.fecha.strftime("%d/%m/%Y")}'


class FotoGaleria(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='fotos_galeria')
    imagen = models.ImageField(upload_to='historial_medico/')
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.imagen and not self.imagen._committed:
            self.imagen = comprimir_imagen(self.imagen)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Foto de {self.paciente.nombre} - {self.fecha_subida}'


class FotoTratamiento(models.Model):
    tratamiento = models.ForeignKey(Tratamiento, on_delete=models.CASCADE, related_name='fotos_tratamiento')
    imagen = models.ImageField(upload_to='tratamientos_extra/')
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.imagen and not self.imagen._committed:
            self.imagen = comprimir_imagen(self.imagen)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Foto extra del tratamiento {self.tratamiento.id}'


@receiver(post_delete, sender=Tratamiento)
def borrar_foto_tratamiento(sender, instance, **kwargs):
    if instance.foto:
        borrar_archivo_storage_async(instance.foto)


@receiver(post_delete, sender=FotoGaleria)
def borrar_foto_galeria(sender, instance, **kwargs):
    if instance.imagen:
        borrar_archivo_storage_async(instance.imagen)


@receiver(post_delete, sender=FotoTratamiento)
def borrar_foto_extra(sender, instance, **kwargs):
    if instance.imagen:
        borrar_archivo_storage_async(instance.imagen)
