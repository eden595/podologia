import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(str, "127.0.0.1,localhost"),
    DJANGO_CSRF_TRUSTED_ORIGINS=(str, ""),
    USE_CLOUDINARY=(bool, False),
    CLOUDINARY_SECURE=(bool, True),
    DB_ENGINE=(str, "django.db.backends.mysql"),
    DB_NAME=(str, "podologia"),
    DB_USER=(str, "root"),
    DB_PASSWORD=(str, ""),
    DB_HOST=(str, "127.0.0.1"),
    DB_PORT=(str, "3306"),
    DB_CONN_MAX_AGE=(int, 60),
)

environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env.bool("DJANGO_DEBUG", default=False)

_secret_fallback = "django-insecure-change-this-key-in-env"
SECRET_KEY = env("DJANGO_SECRET_KEY", default=_secret_fallback)
if not DEBUG and SECRET_KEY == _secret_fallback:
    raise RuntimeError("Configura DJANGO_SECRET_KEY en el archivo .env")

ALLOWED_HOSTS = [
    host.strip()
    for host in env("DJANGO_ALLOWED_HOSTS", default="127.0.0.1,localhost").split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in env("DJANGO_CSRF_TRUSTED_ORIGINS", default="").split(",")
    if origin.strip()
]

cloudinary_url = env("CLOUDINARY_URL", default="").strip()
if cloudinary_url:
    os.environ["CLOUDINARY_URL"] = cloudinary_url

use_cloudinary = env.bool("USE_CLOUDINARY", default=bool(cloudinary_url))
if use_cloudinary and not cloudinary_url:
    raise RuntimeError("USE_CLOUDINARY=True pero CLOUDINARY_URL esta vacio en .env")


INSTALLED_APPS = [
    "pacientes.apps.PacientesConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

if use_cloudinary:
    try:
        import cloudinary  # noqa: F401
        import cloudinary_storage  # noqa: F401
    except ImportError:
        use_cloudinary = False
    else:
        INSTALLED_APPS = ["cloudinary_storage", "cloudinary", *INSTALLED_APPS]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "podologia_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "podologia_project.wsgi.application"


database_url = env("DATABASE_URL", default="").strip()
if database_url:
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    db_engine = env("DB_ENGINE", default="django.db.backends.mysql").strip()
    if db_engine == "django.db.backends.sqlite3":
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": env("DB_NAME", default=str(BASE_DIR / "db.sqlite3")),
            }
        }
    else:
        DATABASES = {
            "default": {
                "ENGINE": db_engine,
                "NAME": env("DB_NAME", default="podologia"),
                "USER": env("DB_USER", default="root"),
                "PASSWORD": env("DB_PASSWORD", default=""),
                "HOST": env("DB_HOST", default="127.0.0.1"),
                "PORT": env("DB_PORT", default="3306"),
            }
        }

DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "es-es"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
_static_dir = BASE_DIR / "static"
STATICFILES_DIRS = [_static_dir] if _static_dir.exists() else []
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")


LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "lista_pacientes"
LOGOUT_REDIRECT_URL = "login"


DATA_UPLOAD_MAX_MEMORY_SIZE = 52_428_800
FILE_UPLOAD_MAX_MEMORY_SIZE = 52_428_800


if use_cloudinary:
    CLOUDINARY_STORAGE = {
        "SECURE": env.bool("CLOUDINARY_SECURE", default=True),
    }
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
