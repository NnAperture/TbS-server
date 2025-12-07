# settings.py - УПРОЩЕННАЯ версия для разработки

"""
Django settings for myproject project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# Quick-start development settings
SECRET_KEY = 'django-insecure-)str2j1-od*djq2p=#i8zma&sgyc@#^b=+s3fpcyioc*3@b=d7'
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [
    'tbs-server-s7vy.onrender.com',
    '127.0.0.1',
    'localhost',
    'k90908k8.beget.tech',
]
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'myapp',
    'handlers',
    'accounts',
    'tgcloud',
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ПРОСТЫЕ НАСТРОЙКИ CORS ДЛЯ РАЗРАБОТКИ
CORS_ALLOW_ALL_ORIGINS = True  # Разрешаем все домены для разработки
CORS_ALLOW_CREDENTIALS = True  # Разрешаем куки

# УПРОЩЕННЫЕ НАСТРОЙКИ CSRF ДЛЯ РАЗРАБОТКИ
CSRF_COOKIE_SECURE = False  # False для HTTP в разработке
CSRF_COOKIE_HTTPONLY = False  # False чтобы JS мог читать токен
CSRF_COOKIE_SAMESITE = 'Lax'  # 'Lax' для разработки
CSRF_USE_SESSIONS = False  # Хранить в cookie
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://k90908k8.beget.tech',
    'https://k90908k8.beget.tech',
    'https://tbs-server-s7vy.onrender.com',
    'http://tbs-server-s7vy.onrender.com',
]

# Настройки сессий
SESSION_ENGINE = 'django.contrib.sessions.backends.file'
SESSION_FILE_PATH = os.path.join(BASE_DIR, 'session_files')
os.makedirs(SESSION_FILE_PATH, exist_ok=True)

SESSION_COOKIE_NAME = 'user_session'
SESSION_COOKIE_AGE = 30 * 24 * 60 * 60
SESSION_COOKIE_SECURE = False  # False для разработки
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Google OAuth
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = 'https://tbs-server-s7vy.onrender.com/oauth/google/callback/'

ROOT_URLCONF = 'myproject.urls'

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

WSGI_APPLICATION = 'myproject.wsgi.application'

# Без БД - используем SQLite для минимальных нужд
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'