# accounts/client.py
import requests
import json
import logging
from django.conf import settings
from urllib.parse import urlencode
import time
import tgcloud as tg
import config
import threading
import secrets

LIFE_TIME = 3600 * 24 * 100

acc_manifest_id = tg.Id().from_str("0|2|4011")
sessions_manifest_id = tg.Id().from_str("0|1|4151")

public_manifest_id = tg.Id().from_str("0|1|4150")
telegram_manifest_id = tg.Id().from_str("0|2|4012")

logger = logging.getLogger(__name__)

class PHPApiClient:
    def __init__(self):
        self.lock = threading.RLock()
        with self.lock:
            manifest = tg.UndefinedVar(id=acc_manifest_id)
            self.accounts:dict = tg.UndefinedVar(id=tg.Id().from_str(manifest.get()[-1])).get()
            self.sessions:dict = tg.UndefinedVar(id=sessions_manifest_id).get()
    
    def __getitem__(self, index):
        return self.accounts[index]

    def _create_user(self, id, email, name):
        with self.lock:
            self.accounts = self.accounts | {id: 
                                             (str((new := tg.UndefinedVar({"id":id,
                                                                      "email":email,
                                                                      "name":name})).id))
                                             }
            def th(self=self):
                with self.lock:
                    v = tg.UndefinedVar(self.accounts)
                    manifest = tg.UndefinedVar(id=acc_manifest_id)
                    manifest.set(manifest.get() + [str(v.id)])
            threading.Thread(target=th).start()
            return new

    def __contains__(self, value):
        return value in self.accounts
    
    def get(self, google_id, email=None, name=None) -> tg.UndefinedVar:
        if(google_id in self):
            return tg.UndefinedVar(id=tg.Id().from_str(self[google_id]))
        else:
            return self._create_user(google_id, email, name)
    
    def create_session(self, id):
        while(session_id := secrets.token_urlsafe(32)) in self.sessions:
            pass
        self.sessions[session_id] = {"id":id,
                                     "time_start":time.time()}
        self._sessions_gc(True)
        return session_id
    
    def _sessions_gc(self, save=False):
        delete = []
        for session in self.sessions:
            if(time.time() - self.sessions[session]["time_start"] > LIFE_TIME):
                delete.append(session)
        for s in delete:
            self.sessions.pop(s)
        if(len(delete) != 0 or save):
            def th(self):
                tg.UndefinedVar(id=sessions_manifest_id).set(self.sessions)
            threading.Thread(target=th).start()
    
    def validate_session(self, token):
        if(token in self.sessions):
            return {"success":True, "user":self.sessions[token]["id"]}
        return {}


php_client = PHPApiClient()
