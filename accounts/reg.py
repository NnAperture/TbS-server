# accounts/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
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
    """Менеджер сессий, использующий наши куки и PHPApiClient"""
    
    @staticmethod
    def set_session_cookies(response, session_token, pub_id):
        """Устанавливает куки сессии"""
        response.set_cookie(
            key='session_token',
            value=session_token,
            max_age=settings.SESSION_COOKIE_AGE,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=True,
            samesite=settings.SESSION_COOKIE_SAMESITE
        )
        
        # pub_id для фронтенда (не HttpOnly, чтобы JS мог читать)
        response.set_cookie(
            key='pub_id',
            value=str(pub_id),
            max_age=settings.SESSION_COOKIE_AGE,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=False,
            samesite=settings.SESSION_COOKIE_SAMESITE
        )
        return response
    
    @staticmethod
    def delete_session_cookies(response):
        """Удаляет куки сессии"""
        response.delete_cookie('session_token')
        response.delete_cookie('pub_id')
        return response
    
    @staticmethod
    def get_session_token(request):
        """Получает токен сессии из запроса"""
        return request.COOKIES.get('session_token')
    
    @staticmethod
    def validate_request(request):
        """Валидирует запрос и возвращает данные пользователя"""
        session_token = SessionManager.get_session_token(request)
        if not session_token:
            return None
        
        session_data = php_client.validate_session(session_token)
        if not session_data.get('success'):
            return None
        
        return session_data['user']

def google_login(request):
    """Перенаправление на Google OAuth с простой state защитой"""
    google_auth_url = 'https://accounts.google.com/o/oauth2/v2/auth'
    
    # Генерируем простой state (можете использовать сессии файловые)
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
    
    # Сохраняем state в cookie вместо сессии БД
    auth_url = f"{google_auth_url}?{urllib.parse.urlencode(params)}"
    
    response = redirect(auth_url)
    response.set_cookie('oauth_state', state, max_age=300)  # 5 минут
    return response

def google_callback(request):
    """Обработка callback от Google"""
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')
    
    # Получаем state из cookie
    saved_state = request.COOKIES.get('oauth_state')
    
    if not saved_state or state != saved_state:
        logger.error("Invalid or missing state parameter")
        return JsonResponse({'error': 'Invalid authentication request'}, status=400)
    
    if error:
        logger.error(f"Google OAuth error: {error}")
        return JsonResponse({'error': f'Google authentication error: {error}'}, status=400)
    
    if not code:
        logger.error("No authorization code received from Google")
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
        
        logger.debug("Requesting token from Google")
        token_response = requests.post(token_url, data=token_data, timeout=30)
        token_response.raise_for_status()
        token_json = token_response.json()
        
        # Получаем информацию о пользователе
        user_info_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
        headers = {'Authorization': f'Bearer {token_json["access_token"]}'}
        
        logger.debug("Requesting user info from Google")
        user_info_response = requests.get(user_info_url, headers=headers, timeout=30)
        user_info_response.raise_for_status()
        user_info = user_info_response.json()
        
        logger.info(f"Google user info received: {user_info.get('email', 'No email')}")
        
        # Сохраняем пользователя в БД
        google_id = user_info['sub']
        email = user_info.get('email')
        name = user_info.get('name')
        
        # Создаем или получаем пользователя
        user_var = php_client.get(google_id=google_id, email=email, name=name)
        user_data = user_var.get()
        
        logger.info(f"User created/retrieved: ID={user_data['id']}, PubID={user_data.get('pub')}")
        
        # Создаем сессию
        session_token = php_client.create_session(user_data['id'])
        logger.info(f"Session token created: {session_token[:10]}...")
        
        # Создаем ответ с редиректом на дашборд
        response = redirect('/dashboard/')
        
        # Устанавливаем куки
        response = SessionManager.set_session_cookies(
            response, 
            session_token, 
            user_data.get('pub')
        )
        
        # Удаляем временный state cookie
        response.delete_cookie('oauth_state')
        
        return response
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request error in google_callback: {str(e)}")
        return JsonResponse({'error': 'Network error during authentication'}, status=500)
    except Exception as e:
        logger.error(f"Unexpected error in google_callback: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)

def dashboard(request):
    """Основной дашборд пользователя"""
    user_data = SessionManager.validate_request(request)
    
    if not user_data:
        # Пользователь не аутентифицирован
        return render(request, 'accounts/login_required.html', {
            'login_url': reverse('google_login')
        })
    
    # Получаем полные данные пользователя из tgcloud
    user_id = user_data['id']
    if user_id in php_client.accounts:
        user_var = tg.UndefinedVar(id=tg.Id().from_str(php_client[user_id]))
        full_user_data = user_var.get()
    else:
        full_user_data = user_data
    
    # Форматируем дату создания
    import datetime
    if 'created_at' in full_user_data:
        created_at = datetime.datetime.fromtimestamp(full_user_data['created_at'])
        full_user_data['created_at_formatted'] = created_at.strftime('%d.%m.%Y %H:%M')
    
    return render(request, 'accounts/dashboard.html', {
        'user': full_user_data,
        'pub_id': user_data.get('pub_id')
    })

@csrf_exempt
def api_user_info(request):
    """API для получения информации о пользователе"""
    user_data = SessionManager.validate_request(request)
    
    if not user_data:
        return JsonResponse({
            'authenticated': False,
            'error': 'Authentication required'
        }, status=401)
    
    # Получаем дополнительные данные если нужно
    user_id = user_data['id']
    if user_id in php_client.accounts:
        user_var = tg.UndefinedVar(id=tg.Id().from_str(php_client[user_id]))
        full_data = user_var.get()
        user_data.update(full_data)
    
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
    response = SessionManager.delete_session_cookies(response)
    
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
        
        # Возвращаем только публичные данные
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

@csrf_exempt
def api_update_profile(request):
    """API для обновления профиля пользователя"""
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
        
        # Обновляем данные пользователя
        success = php_client.update_user_info(user_id, **data)
        
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

def index(request):
    """Главная страница"""
    user_data = SessionManager.validate_request(request)
    
    if user_data:
        return redirect('/dashboard/')
    
    return render(request, 'accounts/index.html')