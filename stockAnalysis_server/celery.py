import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockAnalysis_server.settings')

app = Celery('stockAnalysis_server')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
