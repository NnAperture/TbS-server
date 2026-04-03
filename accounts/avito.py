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
        self.price = None
        self.description = None
        self.author = None
        self.special = {}
        self.id = 0

class Packager:
    def __init__(self, obj=None, id=None):
        self._obj = tg.UndefinedVar(obj, id=id).cache()
    
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
        return
    obj = tg.UndefinedVar(id=av_id)
    obj.set(obj.get() + [pack_id])

def create_product(id, properties):
    prod = Product()
    prod.author = id
    prod.name = properties.get("name", None)
    prod.price = properties.get("price", None)
    prod.icon = properties.get("icon", None)
    prod.description = properties.get("description", None)
    prod.special = properties.get("special", None)

    pack_id = Packager(prod).id
    threading.Thread(target=add_product, args=(id, pack_id)).start()

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
                'pack_id': pack_id.to_str()
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

def get_avito(id):
    avito = tg.UndefinedVar(id=client.get(id)["avito"]).get()
    if(avito == None): avito = []
    return [Packager(id) for id in avito]

@csrf_exempt
def avito_dashboard(request):
    user_data = SessionManager.validate_request(request)

    if not user_data:
        return redirect('/oauth/google/')
    
    user_id = user_data['id']

    avito = list(map(lambda x:x.get_obj, get_avito(user_id)))
    response = render(request, 'avito/dashboard.html', {
        'avito': avito,
        'name': client.get(user_id)["name"]
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

@csrf_exempt
def create_product_page(request):
    user_data = SessionManager.validate_request(request)

    if not user_data:
        return redirect('/oauth/google/')
    
    user_id = user_data['id']

    response = render(request, 'avito/edit_page.html', {
        'name': client.get(user_id)["name"],
        'product': None,
        'id':None
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