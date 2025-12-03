# myapp/urls.py
from django.urls import path
from handlers import handler
from handlers import seccion
from accounts import reg

urlpatterns = [
    path('admin_check/', handler.admin_check, name='admin_check'),
    path('check_code/', handler.check_code, name='check_code'),
    path('update_news0023399/', handler.update_news, name='update_news'),
    path('news_pop/', handler.get_news, name='get_news'),

    path('auth/google/', reg.google_login, name='google_login'),
    path('auth/google/callback/', reg.google_callback, name='google_callback'),
    path('api/validate-session/', reg.validate_session, name='validate_session'),
    path('api/logout/', reg.logout, name='logout'),
    path('settings/', reg.settings_page, name='settings'),
]
