# myapp/urls.py
from django.urls import path
from handlers import handler
from handlers import seccion

import threading
from constant_tasks import task_everyday

threading.Thread(target=task_everyday.delay, daemon=True).start()


urlpatterns = [
    path('admin_check/', handler.admin_check),
    path('check_code/', handler.check_code),
    path('admin_check/', handler.update_news),
]
