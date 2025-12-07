# accounts/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt, csrf_protect
from django.middleware.csrf import get_token, rotate_token
from django.conf import settings
from django.urls import reverse
import requests
import json
import logging
import urllib.parse
import secrets
import tgcloud as tg
from .client import php_client

logger = logging.getLogger(__name__)

class SessionManager:
    """Менеджер сессий"""
    
    @staticmethod
    def get_session_token(request):
        return request.COOKIES.get('session_token')
    
    @staticmethod
    def validate_request(request):
        session_token = SessionManager.get_session_token(request)
        if not session_token:
            return None
        
        session_data = php_client.validate_session(session_token)
        if not session_data.get('success'):
            return None
        
        return session_data['user']

# Упрощенный декоратор для CSRF
def csrf_exempt_if_debug(view_func):
    """Отключает CSRF в режиме разработки"""
    if settings.DEBUG:
        return csrf_exempt(view_func)
    return csrf_protect(view_func)

@ensure_csrf_cookie
def set_csrf_token(request):
    """Явно устанавливает CSRF cookie"""
    response = JsonResponse({'detail': 'CSRF cookie set'})
    response.set_cookie(
        'csrftoken',
        get_token(request),
        max_age=31449600,
        secure=settings.CSRF_COOKIE_SECURE,
        httponly=False,
        samesite=settings.CSRF_COOKIE_SAMESITE
    )
    return response

@ensure_csrf_cookie
def dashboard(request):
    """Основной дашборд пользователя - УПРОЩЕННЫЙ"""
    user_data = SessionManager.validate_request(request)
    
    if not user_data:
        return redirect('/oauth/google/')
    
    # Получаем данные пользователя
    user_id = user_data['id']
    if user_id in php_client.accounts:
        user_var = tg.UndefinedVar(id=tg.Id().from_str(php_client[user_id]))
        full_user_data = user_var.get()
    else:
        full_user_data = user_data
    
    # Форматируем дату
    import datetime
    if 'created_at' in full_user_data:
        created_at = datetime.datetime.fromtimestamp(full_user_data['created_at'])
        full_user_data['created_at_formatted'] = created_at.strftime('%d.%m.%Y %H:%M')
    
    # Устанавливаем CSRF cookie явно
    response = render(request, 'accounts/dashboard.html', {
        'user': full_user_data,
        'pub_id': user_data.get('pub_id'),
    })
    
    # Явно устанавливаем CSRF cookie
    response.set_cookie(
        'csrftoken',
        get_token(request),
        max_age=31449600,
        secure=False,  # False для разработки
        httponly=False,
        samesite='Lax'
    )
    
    return response

# ВРЕМЕННО отключаем CSRF для разработки
@csrf_exempt
def api_update_profile(request):
    """API для обновления профиля пользователя - ВРЕМЕННО БЕЗ CSRF"""
    user_data = SessionManager.validate_request(request)
    
    if not user_data:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)
    
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Method not allowed'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        user_id = user_data['id']
        
        # Простая валидация
        validated_data = {}
        
        if 'name' in data:
            name = data['name'].strip()
            if name and 1 <= len(name) <= 50:
                validated_data['name'] = name
        
        if 'bio' in data:
            bio = data['bio'].strip()
            if len(bio) <= 200:
                validated_data['bio'] = bio
        
        # Обновляем данные
        if validated_data:
            success = php_client.update_user_info(user_id, **validated_data)
            
            if success:
                return JsonResponse({
                    'success': True,
                    'message': 'Profile updated successfully'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to update profile'
                }, status=500)
        else:
            return JsonResponse({
                'success': False,
                'error': 'No valid data to update'
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)

# Остальные функции остаются как были
def google_login(request):
    """Перенаправление на Google OAuth"""
    google_auth_url = 'https://accounts.google.com/o/oauth2/v2/auth'
    
    state = secrets.token_urlsafe(16)
    
    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'consent',
        'state': state
    }
    
    auth_url = f"{google_auth_url}?{urllib.parse.urlencode(params)}"
    
    response = redirect(auth_url)
    response.set_cookie('oauth_state', state, max_age=300)
    return response

def google_callback(request):
    """Обработка callback от Google"""
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')
    
    saved_state = request.COOKIES.get('oauth_state')
    
    if not saved_state or state != saved_state:
        return JsonResponse({'error': 'Invalid authentication request'}, status=400)
    
    if error:
        return JsonResponse({'error': f'Google authentication error: {error}'}, status=400)
    
    if not code:
        return JsonResponse({'error': 'No authorization code received'}, status=400)
    
    try:
        # Получаем токен у Google
        token_url = 'https://oauth2.googleapis.com/token'
        token_data = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': settings.GOOGLE_REDIRECT_URI
        }
        
        token_response = requests.post(token_url, data=token_data, timeout=30)
        token_response.raise_for_status()
        token_json = token_response.json()
        
        # Получаем информацию о пользователе
        user_info_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
        headers = {'Authorization': f'Bearer {token_json["access_token"]}'}
        
        user_info_response = requests.get(user_info_url, headers=headers, timeout=30)
        user_info_response.raise_for_status()
        user_info = user_info_response.json()
        
        # Сохраняем пользователя
        google_id = user_info['sub']
        email = user_info.get('email')
        name = user_info.get('name')
        
        user_var = php_client.get(google_id=google_id, email=email, name=name)
        user_data = user_var.get()
        
        # Создаем сессию
        session_token = php_client.create_session(user_data['id'])
        
        # Создаем ответ
        response = redirect('/dashboard/')
        
        # Устанавливаем куки
        response.set_cookie(
            'session_token',
            session_token,
            max_age=settings.SESSION_COOKIE_AGE,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=True,
            samesite=settings.SESSION_COOKIE_SAMESITE
        )
        
        response.set_cookie(
            'pub_id',
            str(user_data.get('pub')),
            max_age=settings.SESSION_COOKIE_AGE,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=False,
            samesite=settings.SESSION_COOKIE_SAMESITE
        )
        
        # Устанавливаем CSRF cookie
        response.set_cookie(
            'csrftoken',
            get_token(request),
            max_age=31449600,
            secure=False,
            httponly=False,
            samesite='Lax'
        )
        
        response.delete_cookie('oauth_state')
        
        return response
        
    except Exception as e:
        logger.error(f"Error in google_callback: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

@ensure_csrf_cookie
def api_user_info(request):
    """API для получения информации о пользователе"""
    user_data = SessionManager.validate_request(request)
    
    if not user_data:
        return JsonResponse({
            'authenticated': False,
            'error': 'Authentication required'
        }, status=401)
    
    return JsonResponse({
        'authenticated': True,
        'user': user_data
    })

def logout(request):
    """Выход из системы"""
    session_token = SessionManager.get_session_token(request)
    
    if session_token:
        php_client.delete_session(session_token)
    
    response = redirect('/')
    response.delete_cookie('session_token')
    response.delete_cookie('pub_id')
    response.delete_cookie('csrftoken')
    
    return response

@csrf_exempt
def api_get_pub_data(request, pub_id):
    """API для получения публичных данных пользователя по pub_id"""
    try:
        user_data = php_client.get_user_by_pub_id(int(pub_id))
        
        if not user_data:
            return JsonResponse({
                'success': False,
                'error': 'User not found'
            }, status=404)
        
        public_data = {
            'pub_id': user_data.get('pub'),
            'name': user_data.get('name'),
            'created_at': user_data.get('created_at'),
        }
        
        return JsonResponse({
            'success': True,
            'data': public_data
        })
        
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid pub_id format'
        }, status=400)

@ensure_csrf_cookie
def index(request):
    """Главная страница"""
    user_data = SessionManager.validate_request(request)
    
    if user_data:
        return redirect('/dashboard/')
    
    response = render(request, 'accounts/index.html')
    # Устанавливаем CSRF cookie на главной странице
    response.set_cookie(
        'csrftoken',
        get_token(request),
        max_age=31449600,
        secure=False,
        httponly=False,
        samesite='Lax'
    )
    return response