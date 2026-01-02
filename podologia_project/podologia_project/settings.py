import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar el archivo .env
# Esto leerá CLOUDINARY_URL, SECRET_KEY y DB_PASSWORD de tu archivo oculto
env_path = os.path.join(BASE_DIR, '.env')
load_dotenv(env_path)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
# Ojo: En producción real en PythonAnywhere, idealmente esto debería ser False
DEBUG = True 

ALLOWED_HOSTS = ['eden2001.pythonanywhere.com', '127.0.0.1', 'localhost']

# Application definition
INSTALLED_APPS = [
    'cloudinary_storage',
    'cloudinary',
    'pacientes.apps.PacientesConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'podologia_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'podologia_project.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'eden2001$default', 
        'USER': 'eden2001',
        # Aquí usamos la variable de entorno para seguridad
        'PASSWORD': os.getenv('DB_PASSWORD'), 
        'HOST': 'eden2001.mysql.pythonanywhere-services.com',
        'PORT': '3306',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

# Internationalization
LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
# PythonAnywhere usará STATIC_ROOT para servir archivos
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Opcional: Solo si tienes una carpeta 'static' local con CSS propios para desarrollo
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static'),] 

# Media Files (Cloudinary)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Login / Logout config
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'lista_pacientes'
LOGOUT_REDIRECT_URL = 'login'

DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800 
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800

# Configuración Cloudinary
# Ya no hace falta poner os.environ aquí arriba porque load_dotenv ya cargó CLOUDINARY_URL
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'dezml9ony', # Opcional si ya está en la URL, pero bueno tenerlo
    'API_KEY': '914967166155654', # Opcional si ya está en la URL
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'), # Si quisieras separarlo, pero con la URL basta
    'SECURE': True,
}

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}