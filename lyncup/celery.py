from __future__ import absolute_import, unicode_literals
from django.conf import settings
from celery import Celery
import os

#this sets the DJANGO_SETTINGS_MODULE environment variable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lyncup.settings')

#this creates an instance of the celery application
app = Celery('lyncup')

#this tells Celery to use Django project’s settings for its configuration specifically looking for settings that start with the prefix CELERY_, this helps keep Celery-related settings isolated and organised within Django settings file
app.config_from_object('django.conf:settings', namespace='CELERY')

#This line automatically discovers task modules in the installed Django apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)