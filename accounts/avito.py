from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest, JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt, csrf_protect
from django.middleware.csrf import get_token, rotate_token
from django.conf import settings
from django.urls import reverse
import requests
import tgcloud as tg
from .client import client
from .reg import SessionManager
import threading
import json
from accounts.reg import SessionManager

class Product:
    def __init__(self):
        self.icon = None
        self.name = None 
        self.description = None
        self.author = None
        self.special = {}

class Packager:
    def __init__(self, obj=Product()):
        self._obj = tg.UndefinedVar(obj)
    
    def get_obj(self):
        return self._obj.get()
    
    def set_obj(self, obj):
        self._obj.set(obj)
    
    @property
    def id(self):
        return self._obj.id

def add_product(id, pack_id):
    av_id = client.get(id)["avito"]
    if(av_id == None):
        client.update_user_info({"avito":
                                 tg.UndefinedVar([pack_id])})
    obj = tg.UndefinedVar(id=av_id)
    obj.set(obj.get() + [pack_id])

def create_product(id, properties):
    prod = Product()
    prod.author = id
    prod.name = properties.get("name", None)
    prod.icon = properties.get("icon", None)
    prod.description = properties.get("description", None)
    prod.special = properties.get("special", None)

    pack_id = Packager(prod).id
    threading.Thread(target=add_product, args=(id, pack_id))

    return pack_id

@csrf_exempt
def create_product_view(request):
    if request.method == 'POST':
        try:
            user_data = SessionManager.validate_request(request)
            if not user_data:
                return JsonResponse({
                    'authenticated': False,
                    'error': 'Authentication required'
                }, status=401)
            data = json.loads(request.body)
            id = user_data.get("id")
            properties = data.get('properties', {})
            
            pack_id = create_product(id, properties)
            
            return JsonResponse({
                'status': 'success',
                'pack_id': pack_id
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Method not allowed'
        }, status=405)