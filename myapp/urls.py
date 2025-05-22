# myapp/urls.py
from django.urls import path
from handlers import handler
from handlers import seccion

import threading
from constant_tasks import task_everyday
threading(target=task_everyday.delay, daemon=True).start()

urlpatterns = [
    path('acc/', handler.account, name='account'),
    path('seccion/', seccion.seccion, name='seccion'),
    path('visits/', seccion.visits, name='seccion'),
]
