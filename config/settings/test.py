from .base import *

DEBUG = False

# Fast in-memory SQLite for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '100000/day',
    'user': '100000/day',
}

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
