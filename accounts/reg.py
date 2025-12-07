# accounts/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.urls import reverse
from django.middleware.csrf import get_token
import requests
import json
import logging
import urllib.parse
import tgcloud as tg
from .client import php_client

logger = logging.getLogger(__name__)

def google_login(request):
    """Перенаправление на Google OAuth с сохранением состояния"""
    google_auth_url = 'https://accounts.google.com/o/oauth2/v2/auth'
    
    # Генерируем state для защиты от CSRF
    import secrets
    state = secrets.token_urlsafe(16)
    request.session['oauth_state'] = state
    request.session['next_url'] = request.GET.get('next', '/dashboard/')
    
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
    
    logger.info(f"Redirecting to Google OAuth: {auth_url}")
    return redirect(auth_url)

def google_callback(request):
    """Обработка callback от Google с установкой кук в домене Django"""
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')
    
    # Проверяем state для защиты от CSRF
    if state != request.session.get('oauth_state'):
        logger.error("Invalid state parameter")
        return render(request, 'accounts/error.html', {
            'error': 'Invalid authentication request'
        })
    
    if error:
        logger.error(f"Google OAuth error: {error}")
        return render(request, 'accounts/error.html', {
            'error': f'Google authentication error: {error}'
        })
    
    if not code:
        logger.error("No authorization code received from Google")
        return render(request, 'accounts/error.html', {
            'error': 'No authorization code received'
        })
    
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
        
        # Получаем URL для редиректа
        next_url = request.session.get('next_url', '/dashboard/')
        
        # Создаем ответ с редиректом на дашборд
        response = redirect(next_url)
        
        # Устанавливаем куку с сессионным токеном
        response.set_cookie(
            key='session_token',
            value=session_token,
            max_age=settings.SESSION_COOKIE_AGE,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=True,  # Защищаем от XSS
            samesite='Lax',  # Разрешаем кросс-доменные запросы
            domain=settings.SESSION_COOKIE_DOMAIN  # Ваш домен Django
        )
        
        # Также устанавливаем куку с pub_id для фронтенда
        response.set_cookie(
            key='pub_id',
            value=str(user_data.get('pub')),
            max_age=settings.SESSION_COOKIE_AGE,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=False,  # Доступно для JavaScript
            samesite='Lax',
            domain=settings.SESSION_COOKIE_DOMAIN
        )
        
        # Очищаем сессионные данные
        if 'oauth_state' in request.session:
            del request.session['oauth_state']
        if 'next_url' in request.session:
            del request.session['next_url']
        
        return response
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request error in google_callback: {str(e)}")
        return render(request, 'accounts/error.html', {
            'error': 'Network error during authentication'
        })
    except Exception as e:
        logger.error(f"Unexpected error in google_callback: {str(e)}", exc_info=True)
        return render(request, 'accounts/error.html', {
            'error': 'Internal server error'
        })


def dashboard(request):
    """Основной дашборд пользователя"""
    session_token = request.COOKIES.get('session_token')
    
    if not session_token:
        # Пользователь не аутентифицирован
        return render(request, 'accounts/login_required.html', {
            'login_url': reverse('google_login') + '?next=/dashboard/'
        })
    
    # Валидируем сессию
    session_response = php_client.validate_session(session_token)
    
    if not session_response.get('success'):
        response = render(request, 'accounts/login_required.html', {
            'login_url': reverse('google_login') + '?next=/dashboard/'
        })
        response.delete_cookie('session_token')
        response.delete_cookie('pub_id')
        return response
    
    user_info = session_response['user']
    
    # Получаем полные данные пользователя
    if user_info['id'] in php_client.accounts:
        user_var = tg.UndefinedVar(id=tg.Id().from_str(php_client[user_info['id']]))
        full_user_data = user_var.get()
    else:
        full_user_data = user_info
    
    return render(request, 'accounts/dashboard.html', {
        'user': full_user_data,
        'session_token': session_token,
        'pub_id': user_info.get('pub_id'),
        'csrf_token': get_token(request)
    })


@csrf_exempt
def api_user_info(request):
    """API для получения информации о пользователе (для фронтенда)"""
    session_token = request.COOKIES.get('session_token')
    
    if not session_token:
        return JsonResponse({
            'authenticated': False,
            'error': 'No session token'
        }, status=401)
    
    session_response = php_client.validate_session(session_token)
    
    if not session_response.get('success'):
        return JsonResponse({
            'authenticated': False,
            'error': 'Invalid session'
        }, status=401)
    
    user_info = session_response['user']
    
    # Добавляем дополнительную информацию если нужно
    return JsonResponse({
        'authenticated': True,
        'user': user_info
    })


def logout(request):
    """Выход из системы"""
    session_token = request.COOKIES.get('session_token')
    
    if session_token and session_token in php_client.sessions:
        php_client.sessions.pop(session_token)
        php_client._sessions_gc(True)
    
    response = redirect('/')
    response.delete_cookie('session_token')
    response.delete_cookie('pub_id')
    
    return response


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
            # Добавьте другие публичные поля
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
    session_token = request.COOKIES.get('session_token')
    
    if not session_token:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)
    
    session_response = php_client.validate_session(session_token)
    
    if not session_response.get('success'):
        return JsonResponse({
            'success': False,
            'error': 'Invalid session'
        }, status=401)
    
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Method not allowed'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        user_id = session_response['user']['id']
        
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