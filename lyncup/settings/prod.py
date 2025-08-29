from .base import *
from decouple import config

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = True
DEBUG = False


ALLOWED_HOSTS = [config("DJANGO_URL"), f"www.{config('DJANGO_URL')}"]

CORS_ALLOWED_ORIGINS = [
    f"https://{config('FRONTEND_URL')}",
    f"https://www.{config('FRONTEND_URL')}",
]

##not needed as I'm using JWT token
# CSRF_TRUSTED_ORIGINS = [
#     f"https://{config('DJANGO_URL')}",
#     f"https://www.{config('DJANGO_URL')}",
#     f"https://www.{config('FRONTEND_URL')}",
#     f"https://{config('FRONTEND_URL')}",
# ]

CORS_ALLOW_CREDENTIALS = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SAMESITE = 'None'

REDIS_HOST = config('REDIS_HOST', default="redis")  #fallback to "redis" if not in .env
REDIS_PORT = config("REDIS_PORT", default='6379')

REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"


CHANNEL_LAYERS = {
    # a python dict of a configuration for using Redis as a kind of message board essentially it's going to hold all of the data that is all of the messages for each of the rooms. So we're just saying that we're going to use the channel's Redis package that we installed much earlier. And the configuration here, we're going to find Redis at local host, the local IP address and it's going to be running on its default port number 6379, so that when we come to update the app will have to start Redis.
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            # 'hosts': [('127.0.0.1', 6379)]
            # 'hosts': [('localhost', 6379)]
            'hosts': [(REDIS_HOST, int(REDIS_PORT))],

        },

    },

}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL


#What below does:
# Tells Django/WhiteNoise to serve static files (CSS, JS, images) in a production-safe way.
# Adds hashes to filenames (style.7f3ab.css) → browsers always fetch the latest version when you deploy new code.
# Serves compressed versions (gzip, Brotli) → faster load times.
# Why needed: Without this, browsers may cache old static files and not update correctly after deployment.
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

#Forces all HTTP requests to be redirected to HTTPS.
SECURE_SSL_REDIRECT = True


# Optional HSTS once everything is HTTPS-only end-to-end:
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = False
# SECURE_HSTS_PRELOAD = False
