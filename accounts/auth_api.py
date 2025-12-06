# accounts/auth_api.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging
from django.conf import settings
from .client import php_client

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["GET"])
def validate_session(request):
    """Валидация сессии - принимаем токен из кук"""
    try:
        # Получаем токен из кук вместо тела запроса
        session_token = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
        
        if not session_token:
            logger.debug("No session token in cookies")
            return JsonResponse({
                'authenticated': False, 
                'error': 'No session token'
            }, status=401)
        
        logger.debug(f"Validating session token from cookies: {session_token[:10]}...")
        session_response = php_client.validate_session(session_token)
        
        if session_response.get('success'):
            user = session_response['user']
            logger.info(f"Session validated for user: {user.get('email', user.get('google_id', 'Unknown'))}")
            
            response_data = {
                'authenticated': True,
                'user': {
                    'id': user['id'],
                    'google_id': user['google_id'],
                    'email': user.get('email'),
                    'name': user.get('name'),
                    'base_link': user.get('base_link')
                }
            }
            
            response = JsonResponse(response_data)
            
            # Обновляем время жизни куки при успешной валидации
            response.set_cookie(
                key=settings.SESSION_COOKIE_NAME,
                value=session_token,
                max_age=settings.SESSION_COOKIE_AGE,
                secure=settings.SESSION_COOKIE_SECURE,
                httponly=settings.SESSION_COOKIE_HTTPONLY,
                samesite=settings.SESSION_COOKIE_SAMESITE,
                path='/'
            )
            
            return response
        else:
            logger.warning(f"Invalid session: {session_response.get('error', 'Unknown error')}")
            
            # Если сессия невалидна, удаляем куку
            response = JsonResponse({
                'authenticated': False,
                'error': session_response.get('error', 'Invalid session')
            }, status=401)
            
            response.delete_cookie(
                settings.SESSION_COOKIE_NAME,
                path='/',
                samesite=settings.SESSION_COOKIE_SAMESITE
            )
            
            return response
            
    except Exception as e:
        logger.error(f"Error validating session: {str(e)}")
        return JsonResponse({
            'authenticated': False, 
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def logout(request):
    """Выход из системы"""
    try:
        data = json.loads(request.body)
        session_token = data.get('session_token')
        
        if session_token:
            logger.info(f"Deleting session: {session_token[:10]}...")
            php_client.delete_session(session_token)
            
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f"Error in logout: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)