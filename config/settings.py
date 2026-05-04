import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ========== تنظیمات OSGeo4W برای GDAL (اجباری برای GeoDjango) ==========
OSGEO4W_ROOT = r"C:\Users\Lenovo\AppData\Local\Programs\OSGeo4W"

# مسیرهای کتابخانه‌های GDAL/GEOS
os.environ['PATH'] = OSGEO4W_ROOT + r'\bin;' + os.environ.get('PATH', '')
os.environ['GDAL_DATA'] = OSGEO4W_ROOT + r'\share\gdal'
os.environ['PROJ_LIB'] = OSGEO4W_ROOT + r'\share\proj'

# مسیر مستقیم DLL‌ها - بر اساس فایل‌های موجود در سیستم شما
GDAL_LIBRARY_PATH = OSGEO4W_ROOT + r'\bin\gdal312.dll'
GEOS_LIBRARY_PATH = OSGEO4W_ROOT + r'\bin\geos_c.dll'

# ========== تنظیمات پایه Django ==========
SECRET_KEY = 'django-insecure-x3!no^*9w@siwu405r9m+8qvf(zh00n9a@jjfyl25x)*c74#*^'
DEBUG = True
ALLOWED_HOSTS = []

# ========== اپلیکیشن‌های نصب شده ==========
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',  # GeoDjango
    'leaflet',              # نمایش نقشه در Django
    'apps.home',
    'apps.users',
    'apps.parcels',
    'apps.inspections',
    'apps.reports',
    'apps.api',
    "apps.core_admin",
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

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
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

WSGI_APPLICATION = 'config.wsgi.application'

# ========== دیتابیس PostgreSQL با PostGIS ==========
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'gis_db',
        'USER': 'postgres',
        'PASSWORD': 'Si1384fa',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# ========== اعتبارسنجی رمز عبور ==========
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ========== زبان و زمان ==========
LANGUAGE_CODE = 'fa'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

# ========== فایل‌های استاتیک و رسانه ==========
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # برای جمع‌آوری فایل‌های استاتیک در production

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"

# ========== مسیرهای ورود و خروج ==========
LOGIN_URL = "/admin-panel/login/"
LOGIN_REDIRECT_URL = "/admin-panel/"

# ========== تنظیمات Leaflet برای نقشه ==========
LEAFLET_CONFIG = {
    'DEFAULT_CENTER': (35.6892, 51.3890),
    'DEFAULT_ZOOM': 12,
    'MIN_ZOOM': 3,
    'MAX_ZOOM': 18,
    'SCALE': 'both',
    'ATTRIBUTION_PREFIX': 'سامانه مدیریت حدیشهر',
}

# ========== تنظیمات آپلود فایل ==========
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000  # افزایش محدودیت فیلدها برای فرم‌های بزرگ
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB