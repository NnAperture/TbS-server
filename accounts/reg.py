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
from .client import client

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

        session_data = client.validate_session(session_token)
        if not session_data.get('success'):
            return None

        return session_data['user']

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

    user_id = user_data['id']
    if user_id in client.accounts:
        user_var = tg.UndefinedVar(id=tg.Id().from_str(client[user_id]))
        full_user_data = user_var.get()
    else:
        full_user_data = user_data

    import datetime
    if 'created_at' in full_user_data:
        created_at = datetime.datetime.fromtimestamp(full_user_data['created_at'])
        full_user_data['created_at_formatted'] = created_at.strftime('%d.%m.%Y %H:%M')

    print(user_data, user_data.get('show_mail'))
    response = render(request, 'accounts/dashboard.html', {
        'user': full_user_data,
        'pub_id': user_data.get('pub_id'),
        'bio':user_data.get('bio'),
        'show_mail':user_data.get('show_mail'),
    })

    response.set_cookie(
        'csrftoken',
        get_token(request),
        max_age=31449600,
        secure=True,  

        httponly=False,
        samesite='Lax'
    )

    return response

def api_update_profile(request):
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

        validated_data = {}

        if 'name' in data:
            name = data['name'].strip()
            if name and 1 <= len(name) <= 50:
                validated_data['name'] = name
        if 'bio' in data:
            bio = data['bio'].strip()
            if len(bio) <= 200:
                validated_data['bio'] = bio
        if 'show_mail' in data:
            validated_data['show_mail'] = data['show_mail']

        if validated_data:
            success = client.update_user_info(user_id, validated_data)

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

        user_info_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
        headers = {'Authorization': f'Bearer {token_json["access_token"]}'}

        user_info_response = requests.get(user_info_url, headers=headers, timeout=30)
        user_info_response.raise_for_status()
        user_info = user_info_response.json()

        google_id = user_info['sub']
        email = user_info.get('email')
        name = user_info.get('name')

        user_var = client.get(google_id=google_id, email=email, name=name)
        user_data = user_var.get()

        session_token = client.create_session(user_data['id'])

        response = redirect('/dashboard/')

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
        client.delete_session(session_token)

    response = redirect('/')
    response.delete_cookie('session_token')
    response.delete_cookie('pub_id')
    response.delete_cookie('csrftoken')

    return response

@csrf_exempt
def api_get_pub_data(request, pub_id):
    """API для получения публичных данных пользователя по pub_id"""
    try:
        user_data = client.get_user_by_pub_id(int(pub_id))

        if not user_data:
            return JsonResponse({
                'success': False,
                'error': 'User not found'
            }, status=404)

        public_data = {
            'pub_id': user_data.get('pub'),
            'name': user_data.get('name'),
            'email': user_data.get('email'),
            'show_mail': user_data.get('show_mail', True),
            'bio': user_data.get('bio', 'Нет описания'),
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
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
def avatar(request):
    if request.method == "GET":
        pub = request.GET.get("pub_id")

        if request.GET.get('format') == 'image':
            try:
                if pub:
                    user = client.get_user_by_pub_id(pub)
                    if not user: 
                        return get_default_avatar()
                    avatar_id = user.get("avatar", "DEFAULT")
                else:
                    user_data = SessionManager.validate_request(request)
                    if not user_data:
                        return get_default_avatar()

                    user = client.get(user_data["id"])
                    if not user:
                        return get_default_avatar()
                    avatar_id = user.get("avatar", "DEFAULT")

                if not avatar_id or avatar_id == "DEFAULT":
                    return get_default_avatar()

                file_bytes = tg.get_file(tg.Id().from_str(avatar_id))
                if not file_bytes:
                    return get_default_avatar()

                try:
                    from PIL import Image
                    from io import BytesIO
                    image = Image.open(BytesIO(file_bytes))
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    image = image.resize((256, 256), Image.Resampling.LANCZOS)
                    output = BytesIO()
                    image.save(output, format='JPEG', quality=85, optimize=True)
                    image_bytes = output.getvalue()
                    output.close()
                    from django.http import HttpResponse
                    response = HttpResponse(image_bytes, content_type='image/jpeg')
                    response['Cache-Control'] = 'public, max-age=3600'
                    return response

                except Exception as e:
                    print(f"Image processing error: {e}")
                    return get_default_avatar()

            except Exception as e:
                print(f"Avatar fetch error: {e}")
                return get_default_avatar()
        else:
            try:
                if pub:
                    user = client.get_user_by_pub_id(int(pub))
                    if not user:
                        return JsonResponse({
                            'error': f'User with pub_id={pub.__repr__()} not found',
                            'avatar': 'DEFAULT'
                        }, status=404)

                    return JsonResponse({
                        'avatar': user.get("avatar", "DEFAULT"),
                        'pub_id': pub,
                        'user_exists': True
                    })
                else:
                    user_data = SessionManager.validate_request(request)
                    if not user_data:
                        return JsonResponse({
                            'authenticated': False,
                            'error': 'Authentication required'
                        }, status=401)

                    user = client.get(user_data["id"])
                    if not user:
                        return JsonResponse({
                            'error': f'User with id={user_data["id"]} not found',
                            'avatar': 'DEFAULT'
                        }, status=404)

                    return JsonResponse({
                        'avatar': user.get("avatar", "DEFAULT"),
                        'user_id': user_data["id"],
                        'name': user.get("name", "")
                    })

            except Exception as e:
                return JsonResponse({
                    'error': f'Failed to fetch avatar: {str(e)}'
                }, status=500)

    elif request.method == "POST":
        user_data = SessionManager.validate_request(request)
        if not user_data:
            return JsonResponse({
                'authenticated': False,
                'error': 'Authentication required'
            }, status=401)

        if 'image' not in request.FILES:
            return JsonResponse({
                'error': 'No image provided'
            }, status=400)

        if request.FILES['image'].size > 10 * 1024 * 1024:
            return JsonResponse({
                'error': 'File too large. Maximum size is 10MB'
            }, status=400)

        image_file = request.FILES['image']
        try:
            from PIL import Image
            from io import BytesIO

            image = Image.open(image_file)
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')

            image = image.resize((256, 256), Image.Resampling.LANCZOS)

            output = BytesIO()
            image.save(output, format='JPEG', quality=95, optimize=True)
            prepared = output.getvalue()
            output.close()
            image_file.close()

            avatar_id = tg.send_file(prepared).to_str()
            client.update_user_info(user_data["id"], {"avatar": avatar_id})

            return JsonResponse({
                'success': True, 
                'avatar_id': avatar_id,
                'image_url': f'/avatar/?pub_id={user_data.get("pub", "")}&format=image'
            })

        except ImportError as e:
            return JsonResponse({
                'error': f'Server configuration error: {str(e)}'
            }, status=500)
        except Exception as e:
            return JsonResponse({
                'error': f'Image processing failed: {str(e)}'
            }, status=400)

    return JsonResponse({
        'error': 'Method not allowed'
    }, status=405)

def get_default_avatar():
    """Генерация дефолтного аватара"""
    try:
        from PIL import Image, ImageDraw
        from io import BytesIO

        image = Image.new('RGB', (256, 256), color=(220, 220, 220))
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 0, 255, 255], outline=(180, 180, 180))
        draw.ellipse([50, 50, 206, 206], fill=(200, 200, 200))
        try:
            from PIL import ImageFont
            try:
                font = ImageFont.truetype("arial.ttf", 100)
            except:
                font = ImageFont.load_default()
            draw.text((128, 128), "U", font=font, fill=(100, 100, 100), anchor="mm")
        except:
            draw.polygon([(128, 80), (100, 140), (100, 180), (156, 180), (156, 140)], 
                         fill=(100, 100, 100))

        output = BytesIO()
        image.save(output, format='JPEG', quality=85)
        image_bytes = output.getvalue()
        output.close()

        response = HttpResponse(image_bytes, content_type='image/jpeg')
        response['Cache-Control'] = 'public, max-age=86400'
        return response

    except Exception as e:
        print(f"Default avatar error: {e}")
        response = HttpResponse(b'', content_type='image/jpeg')
        response.status_code = 200
        return response

