from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent


# -----------------------------------------
# Security
# -----------------------------------------

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-dartalink-development-key"
)

DEBUG = os.getenv("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    ".vercel.app",
]


# -----------------------------------------
# Applications
# -----------------------------------------

INSTALLED_APPS = [

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "corsheaders",

    "rest_framework",

    "workflow",
]


# -----------------------------------------
# Middleware
# -----------------------------------------

MIDDLEWARE = [

    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.security.SecurityMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "core.urls"


# -----------------------------------------
# Templates
# -----------------------------------------

TEMPLATES = [

    {
        "BACKEND":
            "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "templates"
        ],

        "APP_DIRS": True,

        "OPTIONS": {

            "context_processors": [

                "django.template.context_processors.request",

                "django.contrib.auth.context_processors.auth",

                "django.contrib.messages.context_processors.messages",

            ],
        },
    },

]


WSGI_APPLICATION = "core.wsgi.application"


# -----------------------------------------
# Database
# -----------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")


if DATABASE_URL:

    DATABASES = {

        "default":
            dj_database_url.parse(
                DATABASE_URL,
                conn_max_age=600,
                ssl_require=True,
            )

    }

else:

    DATABASES = {

        "default": {

            "ENGINE":
                "django.db.backends.sqlite3",

            "NAME":
                BASE_DIR / "db.sqlite3",

        }

    }


# -----------------------------------------
# Password Validation
# -----------------------------------------

AUTH_PASSWORD_VALIDATORS = [

    {
        "NAME":
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },

    {
        "NAME":
            "django.contrib.auth.password_validation.MinimumLengthValidator",
    },

    {
        "NAME":
            "django.contrib.auth.password_validation.CommonPasswordValidator",
    },

    {
        "NAME":
            "django.contrib.auth.password_validation.NumericPasswordValidator",
    },

]


# -----------------------------------------
# Internationalization
# -----------------------------------------

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kathmandu"

USE_I18N = True

USE_TZ = True


# -----------------------------------------
# Static Files
# -----------------------------------------

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static"
]

STATIC_ROOT = BASE_DIR / "staticfiles"


# -----------------------------------------
# REST Framework
# -----------------------------------------

REST_FRAMEWORK = {

    "DEFAULT_PERMISSION_CLASSES": [

        "rest_framework.permissions.AllowAny"

    ],

}


# -----------------------------------------
# CORS
# -----------------------------------------

CORS_ALLOW_ALL_ORIGINS = DEBUG


# -----------------------------------------
# Default Primary Key
# -----------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"