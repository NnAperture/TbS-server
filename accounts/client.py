# accounts/client.py
import requests
import json
import logging
from django.conf import settings
from urllib.parse import urlencode
import time

logger = logging.getLogger(__name__)

class PHPApiClient:
    def __init__(self):
        self.base_url = settings.PHP_API_URL.rstrip('/')
        self.secret = settings.PHP_API_SECRET
        self.timeout = 30
        
        # Создаем сессию с настройками браузера
        self.session = requests.Session()
        
        # Полный набор заголовков браузера (Chrome)
        self.session.headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.secret}',
            'Origin': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else self.base_url,
            'Referer': f'{self.base_url}/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest'
        })
        self.max_retries = 3
        self.retry_delay = 1
    
    def _make_request(self, action, data=None):
        for attempt in range(self.max_retries):
            try:
                # 1. Формируем URL с GET параметрами
                params = {'action': action}
                url = f"{self.base_url}/user_api.php"
                
                # 2. Добавляем timestamp для избежания кэширования
                params['_'] = int(time.time() * 1000)
                
                # 3. Логируем
                logger.debug(f"PHP API Request [{attempt+1}/{self.max_retries}]:")
                logger.debug(f"  URL: {url}")
                logger.debug(f"  Params: {params}")
                logger.debug(f"  Data: {data}")
                logger.debug(f"  Headers: {dict(self.session.headers)}")
                
                # 4. Делаем запрос
                response = self.session.post(
                    url,
                    params=params,  # GET параметры
                    json=data,      # POST данные
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                # 5. Логируем ответ
                logger.debug(f"PHP API Response:")
                logger.debug(f"  Status: {response.status_code}")
                logger.debug(f"  Headers: {dict(response.headers)}")
                logger.debug(f"  Content: {response.text[:500]}")
                
                # 6. Обрабатываем ответ
                if response.status_code == 403:
                    logger.warning(f"403 Forbidden. Attempt {attempt+1}")
                    
                    # Если это первая попытка, пробуем альтернативный подход
                    if attempt == 0:
                        # Пробуем GET вместо POST
                        return self._try_get_request(url, params, data)
                    elif attempt == 1:
                        # Пробуем без Authorization header
                        temp_headers = self.session.headers.copy()
                        if 'Authorization' in temp_headers:
                            del temp_headers['Authorization']
                        response = self.session.post(
                            url, params=params, json=data,
                            headers=temp_headers, timeout=self.timeout
                        )
                
                response.raise_for_status()
                
                # 7. Парсим JSON
                try:
                    result = response.json()
                    logger.debug(f"Parsed JSON: {result}")
                    return result
                except json.JSONDecodeError:
                    # Возможно, возвращается чистый текст или HTML
                    logger.warning(f"Response is not JSON: {response.text[:200]}")
                    # Пробуем разные форматы
                    if response.text.strip() == '1' or response.text.strip().lower() == 'success':
                        return {'status': 'success'}
                    else:
                        return {'status': 'ok', 'response': response.text}
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed (attempt {attempt+1}): {str(e)}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    raise Exception(f"PHP API request failed after {self.max_retries} attempts: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                raise
    
    def _try_get_request(self, url, params, data):
        """Альтернативный метод: отправляем все данные как GET параметры"""
        try:
            # Добавляем данные к GET параметрам
            if data:
                for key, value in data.items():
                    if value is not None:
                        params[key] = value
            
            logger.debug(f"Trying GET request with params: {params}")
            
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            
            logger.debug(f"GET Response: {response.status_code} - {response.text[:200]}")
            response.raise_for_status()
            
            return response.json() if response.text.strip() else {'status': 'success'}
            
        except Exception as e:
            logger.error(f"GET request also failed: {str(e)}")
            raise
    
    def _test_connection(self):
        """Метод для тестирования подключения"""
        try:
            test_params = {'action': 'test', '_': int(time.time() * 1000)}
            response = self.session.get(
                self.base_url + "/user_api.php",
                params=test_params,
                timeout=10
            )
            return {
                'status': response.status_code,
                'headers': dict(response.headers),
                'body_preview': response.text[:200]
            }
        except Exception as e:
            return {'error': str(e)}
    
    # Остальные методы остаются без изменений
    def get_or_create_user(self, google_id, base_link, email=None, name=None):
        data = {
            'google_id': google_id,
            'base_link': base_link,
            'email': email,
            'name': name
        }
        return self._make_request('get_user_by_google', data)
    
    def create_session(self, user_id):
        data = {'user_id': user_id}
        return self._make_request('create_session', data)
    
    def validate_session(self, session_token):
        data = {'session_token': session_token}
        return self._make_request('validate_session', data)
    
    def delete_session(self, session_token):
        data = {'session_token': session_token}
        return self._make_request('delete_session', data)

# Глобальный экземпляр клиента
php_client = PHPApiClient()
