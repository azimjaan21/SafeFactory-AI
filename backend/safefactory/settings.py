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
    "ppe": BASE_DIR / "ai_models" / "ppe.pt",
    "work_situation": BASE_DIR / "ai_models" / "work_situation.pt",
    "smoke_fire": BASE_DIR / "ai_models" / "fire.pt",
    "worker_forklift": BASE_DIR / "ai_models" / "forklift.pt",
    "pose_anchor": BASE_DIR / "ai_models" / "yolo11s-pose.pt",
}

SAFEFACTORY_RESULT_HISTORY_LIMIT = int(os.getenv("SAFEFACTORY_RESULT_HISTORY_LIMIT", "200"))
SAFEFACTORY_RESULTS_PAGE_SIZE = int(os.getenv("SAFEFACTORY_RESULTS_PAGE_SIZE", "10"))
SAFEFACTORY_EVENT_COOLDOWN_SECONDS = float(os.getenv("SAFEFACTORY_EVENT_COOLDOWN_SECONDS", "300"))
SAFEFACTORY_FORKLIFT_WARNING_DISTANCE = int(os.getenv("SAFEFACTORY_FORKLIFT_WARNING_DISTANCE", "400"))
SAFEFACTORY_FORKLIFT_DANGER_DISTANCE = int(os.getenv("SAFEFACTORY_FORKLIFT_DANGER_DISTANCE", "200"))
SAFEFACTORY_DEFAULT_CONFIDENCE = float(os.getenv("SAFEFACTORY_DEFAULT_CONFIDENCE", "0.25"))
SAFEFACTORY_POSE_CONFIDENCE = float(os.getenv("SAFEFACTORY_POSE_CONFIDENCE", "0.15"))
SAFEFACTORY_MAX_STREAM_MODELS = int(os.getenv("SAFEFACTORY_MAX_STREAM_MODELS", "2"))
# Process every Nth frame for video/RTSP (1 = every frame, 2 = every other frame, 3 = every 3rd frame)
# Higher value = faster playback but lower detection frequency
SAFEFACTORY_STREAM_SKIP_FRAMES = int(os.getenv("SAFEFACTORY_STREAM_SKIP_FRAMES", "2"))

# FP16 (half precision) inference. Off by default: some GPUs/drivers (e.g. cards
# without tensor cores, or mismatched CUDA/cuBLAS builds) crash with
# "CUBLAS_STATUS_NOT_SUPPORTED" on the attention layers of newer YOLO models when
# running in half precision, which can hang/crash the GPU driver. FP32 is slower
# but works everywhere. Set to "1" only if your GPU/driver combo is confirmed stable.
SAFEFACTORY_USE_HALF_PRECISION = os.getenv("SAFEFACTORY_USE_HALF_PRECISION", "0") == "1"

# Abnormal behavior detection settings
# SAFEFACTORY_STREAM_FPS: assumed FPS for timing calculations (step freq, angle rate, inactivity timer)
SAFEFACTORY_STREAM_FPS = float(os.getenv("SAFEFACTORY_STREAM_FPS", "25.0"))
# SAFEFACTORY_INACTIVITY_TIMEOUT_SECONDS: stillness duration before inactivity alert fires
SAFEFACTORY_INACTIVITY_TIMEOUT_SECONDS = float(os.getenv("SAFEFACTORY_INACTIVITY_TIMEOUT_SECONDS", "300.0"))

SAFEFACTORY_DEMO_VIDEO_DIR = Path(os.getenv("SAFEFACTORY_DEMO_VIDEO_DIR", str(BASE_DIR / "demo_video")))
