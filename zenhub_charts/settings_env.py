from .settings import *  # noqa
import os

GITHUB = {
    'token': os.environ['GITHUB_TOKEN'],
    'owner': os.environ['GITHUB_OWNER']
}
ZENHUB = {
    'token': os.environ['ZENHUB_TOKEN']
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_HOST'],
        'PORT': os.environ['DB_PORT']
    }
}


CELERY_BROKER_URL = os.environ['CELERY_BROKER_URL']
CELERY_RESULT_BACKEND = 'redis'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']
