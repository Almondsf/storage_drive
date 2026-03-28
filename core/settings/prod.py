from .base import *

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# In production, enforce HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True