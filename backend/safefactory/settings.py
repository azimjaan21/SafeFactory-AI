import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-dev-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "apps.inference",
]

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

ROOT_URLCONF = "safefactory.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "safefactory.wsgi.application"
ASGI_APPLICATION = "safefactory.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Asia/Seoul")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK = {
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

SAFEFACTORY_MODEL_PATHS = {
    "ppe": PROJECT_ROOT / "ai_models" / "ppe.pt",
    "work_situation": PROJECT_ROOT / "ai_models" / "work_situation.pt",
    "smoke_fire": PROJECT_ROOT / "ai_models" / "fire.pt",
    "worker_forklift": PROJECT_ROOT / "ai_models" / "forklift.pt",
    "pose_anchor": PROJECT_ROOT / "ai_models" / "yolo11s-pose.pt",
}

SAFEFACTORY_RESULT_HISTORY_LIMIT = int(os.getenv("SAFEFACTORY_RESULT_HISTORY_LIMIT", "200"))
SAFEFACTORY_RESULTS_PAGE_SIZE = int(os.getenv("SAFEFACTORY_RESULTS_PAGE_SIZE", "10"))
SAFEFACTORY_EVENT_COOLDOWN_SECONDS = float(os.getenv("SAFEFACTORY_EVENT_COOLDOWN_SECONDS", "300"))
SAFEFACTORY_FORKLIFT_WARNING_DISTANCE = int(os.getenv("SAFEFACTORY_FORKLIFT_WARNING_DISTANCE", "400"))
SAFEFACTORY_FORKLIFT_DANGER_DISTANCE = int(os.getenv("SAFEFACTORY_FORKLIFT_DANGER_DISTANCE", "200"))
SAFEFACTORY_DEFAULT_CONFIDENCE = float(os.getenv("SAFEFACTORY_DEFAULT_CONFIDENCE", "0.35"))
SAFEFACTORY_MAX_STREAM_MODELS = int(os.getenv("SAFEFACTORY_MAX_STREAM_MODELS", "2"))
