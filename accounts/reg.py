from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import requests
import json
import logging
from .client import php_client

logger = logging.getLogger(__name__)

def google_login(request):
    """Перенаправление на Google OAuth"""
    google_auth_url = 'https://accounts.google.com/o/oauth2/v2/auth'
    
    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    auth_url = f"{google_auth_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    
    logger.info(f"Redirecting to Google OAuth: {auth_url}")
    return redirect(auth_url)

def google_callback(request):
    """Обработка callback от Google"""
    code = request.GET.get('code')
    error = request.GET.get('error')
    
    if error:
        logger.error(f"Google OAuth error: {error}")
        return JsonResponse({'error': f'Google OAuth error: {error}'}, status=400)
    
    if not code:
        logger.error("No authorization code received from Google")
        return JsonResponse({'error': 'No authorization code received'}, status=400)
    
    logger.info("Received authorization code from Google")
    
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
        
        if 'access_token' not in token_json:
            logger.error("No access token in Google response")
            return JsonResponse({'error': 'Failed to get access token from Google'}, status=400)
        
        # Получаем информацию о пользователе
        user_info_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
        headers = {'Authorization': f'Bearer {token_json["access_token"]}'}
        
        logger.debug("Requesting user info from Google")
        user_info_response = requests.get(user_info_url, headers=headers, timeout=30)
        user_info_response.raise_for_status()
        user_info = user_info_response.json()
        
        logger.info(f"Google user info received: {user_info.get('email', 'No email')}")
        
        # Сохраняем пользователя в БД через PHP API
        google_id = user_info['sub']
        base_link = f"https://api.example.com/users/{google_id}"  # Замените на реальный base_link
        email = user_info.get('email')
        name = user_info.get('name')
        
        logger.info(f"Creating/updating user in database: {email}")
        
        # Создаем или получаем пользователя
        user_response = php_client.get_or_create_user(
            google_id=google_id,
            base_link=base_link,
            email=email,
            name=name
        )
        
        if not user_response.get('success'):
            logger.error(f"Failed to create user: {user_response}")
            return JsonResponse({'error': 'Failed to create user in database'}, status=500)
        
        user = user_response['user']
        logger.info(f"User created/retrieved: ID={user['id']}")
        
        # Создаем сессию
        logger.info("Creating session for user")
        session_response = php_client.create_session(user['id'])
        
        if not session_response.get('success'):
            logger.error(f"Failed to create session: {session_response}")
            return JsonResponse({'error': 'Failed to create session'}, status=500)
        
        session_token = session_response['session_token']
        logger.info("Session created successfully")
        
        # Перенаправляем на фронтенд с токеном сессии
        frontend_url = f"http://your-frontend-server.com/auth/success?session={session_token}"
        
        response = redirect(frontend_url)
        # Устанавливаем куку для сессии
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=session_token,
            max_age=settings.SESSION_COOKIE_AGE,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            samesite=settings.SESSION_COOKIE_SAMESITE,
            path='/',
            domain=None
        )
        
        logger.info(f"Redirecting to frontend: {frontend_url}")
        return response
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request error in google_callback: {str(e)}")
        return JsonResponse({'error': f'HTTP request failed: {str(e)}'}, status=500)
    except Exception as e:
        logger.error(f"Unexpected error in google_callback: {str(e)}")
        return JsonResponse({'error': f'Internal server error: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST", "GET"])
def validate_session(request):
    """Валидация сессии (для AJAX запросов с фронтенда)"""
    logger.debug(f"validate_session called. Method: {request.method}")
    
    # Для GET запросов - просто возвращаем информацию о методе
    if request.method == 'GET':
        return JsonResponse({
            'method': 'GET',
            'message': 'Use POST method to validate session'
        })
    
    # Для POST запросов - валидируем сессию
    session_token = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
    
    if not session_token:
        logger.warning("No session token in cookies")
        return JsonResponse({'authenticated': False, 'error': 'No session token'}, status=401)
    
    logger.debug(f"Validating session token: {session_token[:10]}...")
    
    try:
        session_response = php_client.validate_session(session_token)
        
        if session_response.get('success'):
            user = session_response['user']
            logger.info(f"Session validated successfully for user: {user.get('email', 'No email')}")
            return JsonResponse({
                'authenticated': True,
                'user': {
                    'id': user['id'],
                    'google_id': user['google_id'],
                    'email': user.get('email'),
                    'name': user.get('name'),
                    'base_link': user.get('base_link')
                }
            })
        else:
            logger.warning(f"Invalid session: {session_response.get('error', 'Unknown error')}")
            return JsonResponse({
                'authenticated': False,
                'error': session_response.get('error', 'Invalid session')
            }, status=401)
            
    except Exception as e:
        logger.error(f"Error validating session: {str(e)}")
        return JsonResponse({
            'authenticated': False,
            'error': f'Validation error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def logout(request):
    """Выход из системы"""
    session_token = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
    
    if session_token:
        try:
            php_client.delete_session(session_token)
            logger.info(f"Session deleted: {session_token[:10]}...")
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            # Продолжаем выполнение даже если не удалось удалить сессию
    
    response = JsonResponse({'success': True})
    response.delete_cookie(
        settings.SESSION_COOKIE_NAME,
        path='/',
        domain=None
    )
    
    return response