# accounts/client.py
import requests
import json
import logging
from django.conf import settings
import time
import tgcloud as tg
import config
import threading
import secrets

LIFE_TIME = 3600 * 24 * 100

acc_manifest_id = tg.Id().from_str("0|2|4011")
sessions_manifest_id = tg.Id().from_str("0|1|4151")
public_manifest_id = tg.Id().from_str("0|1|4150")
pub_id_id = tg.Id().from_str("0|1|4154")
telegram_manifest_id = tg.Id().from_str("0|2|4012")

pub_id_v = tg.Int(id=pub_id_id)

logger = logging.getLogger(__name__)

class PHPApiClient:
    def __init__(self):
        self.lock = threading.RLock()
        with self.lock:
            manifest = tg.UndefinedVar(id=acc_manifest_id)
            self.accounts: dict = tg.UndefinedVar(id=tg.Id().from_str(manifest.get()[-1])).get()
            self.sessions: dict = tg.UndefinedVar(id=sessions_manifest_id).get()
            self.public: dict = tg.UndefinedVar(id=public_manifest_id).get()
            self.telegram: dict = tg.UndefinedVar(id=telegram_manifest_id).get()
    
    def __getitem__(self, index):
        return self.accounts[index]

    def _create_user(self, id, email, name):
        with self.lock:
            pub_id = pub_id_v.get()
            pub_id_v += 1
            user_data = {
                "id": id,
                "email": email,
                "name": name,
                "pub": pub_id,
                "google_id": id,
                "created_at": time.time()
            }
            
            new_user = tg.UndefinedVar(user_data)
            self.accounts = self.accounts | {id: str(new_user.id)}
            self.public = self.public | {pub_id: id}
            
            def th():
                with self.lock:
                    v = tg.UndefinedVar(self.accounts)
                    manifest = tg.UndefinedVar(id=acc_manifest_id)
                    manifest.set(manifest.get() + [str(v.id)])
            threading.Thread(target=th).start()
            return new_user

    def __contains__(self, value):
        return value in self.accounts
    
    def get(self, google_id, email=None, name=None) -> tg.UndefinedVar:
        if google_id in self:
            return tg.UndefinedVar(id=tg.Id().from_str(self[google_id]))
        else:
            return self._create_user(google_id, email, name)
    
    def create_session(self, user_id):
        """Создает сессию в нашей системе (не Django)"""
        while (session_id := secrets.token_urlsafe(32)) in self.sessions:
            pass
        
        self.sessions[session_id] = {
            "user_id": user_id,
            "created_at": time.time(),
            "last_activity": time.time()
        }
        self._sessions_gc(True)
        return session_id
    
    def _sessions_gc(self, save=False):
        """Очистка старых сессий"""
        delete = []
        for session_id, session_data in list(self.sessions.items()):
            if time.time() - session_data.get("last_activity", 0) > LIFE_TIME:
                delete.append(session_id)
        
        for session_id in delete:
            self.sessions.pop(session_id)
        
        if delete or save:
            def th():
                tg.UndefinedVar(id=sessions_manifest_id).set(self.sessions)
            threading.Thread(target=th).start()
    
    def validate_session(self, session_token):
        """Валидация сессии из нашей системы"""
        if session_token in self.sessions:
            # Обновляем время последней активности
            self.sessions[session_token]["last_activity"] = time.time()
            
            # Получаем данные пользователя
            user_id = self.sessions[session_token]["user_id"]
            if user_id in self.accounts:
                user_var = tg.UndefinedVar(id=tg.Id().from_str(self[user_id]))
                user_data = user_var.get()
                
                return {
                    "success": True,
                    "user": {
                        "id": user_data.get("id"),
                        "pub_id": user_data.get("pub"),
                        "email": user_data.get("email"),
                        "name": user_data.get("name"),
                        "google_id": user_data.get("google_id")
                    }
                }
        
        return {"success": False}
    
    def get_user_by_pub_id(self, pub_id):
        """Получить пользователя по публичному ID"""
        if pub_id in self.public:
            user_id = self.public[pub_id]
            if user_id in self.accounts:
                user_var = tg.UndefinedVar(id=tg.Id().from_str(self[user_id]))
                return user_var.get()
        return None
    
    def update_user_info(self, user_id, **kwargs):
        """Обновить информацию о пользователе"""
        if user_id in self.accounts:
            user_var = tg.UndefinedVar(id=tg.Id().from_str(self[user_id]))
            user_data = user_var.get()
            user_data.update(kwargs)
            user_var.set(user_data)
            return True
        return False
    
    def delete_session(self, session_token):
        """Удалить сессию"""
        if session_token in self.sessions:
            self.sessions.pop(session_token)
            self._sessions_gc(True)
            return True
        return False


php_client = PHPApiClient()