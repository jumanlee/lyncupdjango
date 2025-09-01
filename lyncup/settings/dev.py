from .base import *
from decouple import config

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = True
DEBUG = True

# # commented out localhost
# ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "django", config("DJANGO_URL")]
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# # commented out localhost
# CORS_ALLOWED_ORIGINS = ['http://localhost:5173', f"https://{config('FRONTEND_URL')}", f"https://www.{config('FRONTEND_URL')}"]
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

##not needed as I'm using JWT token
# CSRF_TRUSTED_ORIGINS = [
#     "http://localhost:5173",
#     "http://127.0.0.1:5173",
# ]

CORS_ALLOW_CREDENTIALS = True

# In dev we don't sit behind a TLS-terminating proxy
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Use non-secure cookies locally so http:// works
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'

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

# #can swap for below for local testing and Django will just print the email body to the terminal:
# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

#base URL where React frontend handles email verification
#It forms the beginning of the link the user clicks to confirm their email, like this:
#http://localhost:5173/verify-email/<uidb64>/<token>
# FRONTEND_VERIFY_URL = "http://localhost:5173/verify-email"  
# BACKEND_VERIFY_URL = "http://localhost:8080/api/users/verify-email"
BACKEND_VERIFY_URL = "http://localhost:8000/api/users/verify-email"
FRONTEND_VERIFY_SUCCESS_URL = "http://localhost:5173/verify-success"
FRONTEND_VERIFY_FAIL_URL = "http://localhost:5173/verify-fail"

FRONTEND_RESET_PASSWORD_URL = "http://localhost:5173/reset-password"
FRONTEND_RESET_PASSWORD_FAIL_URL = "http://localhost:5173/reset-password-fail"
