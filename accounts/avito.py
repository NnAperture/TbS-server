from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
import tgcloud as tg
from .client import client
from .reg import SessionManager
import threading
import json
import time

PUBLIC_ID = tg.Id().from_str("0|1|4259")
public_list = tg.UndefinedVar(id=PUBLIC_ID)

def create_product_dict(author_id=None, properties=None):
    product = {
        'icon': None,
        'name': None,
        'price': None,
        'description': None,
        'backcom': None,
        'author': author_id,
        'special': {},
        'type': "",
    }
    
    if properties:
        for key, value in properties.items():
            if key in product:
                product[key] = value
            elif key == 'special' and isinstance(value, dict):
                product['special'] = value
            elif key == 'tags':
                product['special']['tags'] = value
                product['special']['time'] = time.time()
    
    return product

class Packager:
    def __init__(self, obj=None, id=None):
        self._obj = tg.UndefinedVar(obj, id=id).cache()
    
    def get_obj(self):
        try:
            value = self._obj.get()
            if value is None:
                return None
            if isinstance(value, dict):
                return value
            # Если value - строка (ID)
            if isinstance(value, str) and '|' in value:
                return tg.UndefinedVar(id=tg.Id().from_str(value)).get()
            return None
        except Exception as e:
            print(f"Error in get_obj: {e}")
            return None
    
    def set_obj(self, obj):
        try:
            current_id = self._obj.get()
            if isinstance(current_id, str) and '|' in current_id:
                tg.UndefinedVar(id=tg.Id().from_str(current_id)).set(obj)
            else:
                self._obj.set(obj)
        except Exception as e:
            print(f"Error in set_obj: {e}")
    
    @property
    def id(self):
        return self._obj.id

def add_product_to_user(user_id, product_id):
    av_data = client.get(user_id).get("avito")
    if av_data is None:
        new_list_id = str(tg.UndefinedVar([product_id]).id)
        client.update_user_info(user_id, {"avito": new_list_id})
    else:
        product_list = tg.UndefinedVar(id=tg.Id().from_str(av_data))
        current_ids = product_list.get()
        current_ids.append(product_id)
        product_list.set(current_ids)

def create_product(user_id, properties):
    product = create_product_dict(author_id=user_id, properties=properties)
    packager = Packager(product)
    product_id = str(packager.id)
    threading.Thread(target=add_product_to_user, args=(user_id, product_id)).start()
    return product_id

@csrf_exempt
def create_product_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        user_data = SessionManager.validate_request(request)
        if not user_data:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        product_id = request.GET.get('id', '').strip('"')
        if not product_id:
            return JsonResponse({'error': 'Product ID required'}, status=400)
        
        print(f"Editing product ID: {product_id}")
        
        properties = json.loads(request.body)
        user_id = user_data.get("id")
        
        required_fields = ['name', 'price', 'backcom', 'type']
        missing = [f for f in required_fields if not properties.get(f)]
        if missing:
            return JsonResponse({'error': f'Missing fields: {missing}'}, status=400)
        
        tg_id = tg.Id().from_str(product_id)
        product_var = tg.UndefinedVar(id=tg_id)
        
        current_time = time.time()
        
        public = public_list.get()
        
        existing_product = product_var.get()
        
        if not existing_product:
            return JsonResponse({'error': 'Product not found'}, status=404)
        
        if str(existing_product.get('author')) != str(user_id):
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        for key, value in properties.items():
            if key in existing_product:
                existing_product[key] = value
            elif key == 'tags':
                if 'special' not in existing_product:
                    existing_product['special'] = {}
                existing_product['special']['tags'] = value
        
        if 'special' not in existing_product:
            existing_product['special'] = {}
        existing_product['special']['time'] = current_time
        
        try:
            product_var.set(existing_product)
        except:
            try:
                product_var.cache().set(existing_product)
            except Exception as e:
                print(f"Error saving: {e}")
        
        if tg_id in public:
            public[tg_id] = current_time
            public_list.set(public)
            print(f"Updated public time for {product_id} to {current_time}")
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        print(f"Edit error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def edit_product_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        user_data = SessionManager.validate_request(request)
        if not user_data:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        product_id = request.GET.get('id', '').strip('"')
        if not product_id:
            return JsonResponse({'error': 'Product ID required'}, status=400)
        
        print(f"Editing product ID: {product_id}")
        
        properties = json.loads(request.body)
        user_id = user_data.get("id")
        
        required_fields = ['name', 'price', 'backcom', 'type']
        missing = [f for f in required_fields if not properties.get(f)]
        if missing:
            return JsonResponse({'error': f'Missing fields: {missing}'}, status=400)
        
        tg_id = tg.Id().from_str(product_id)
        product_var = tg.UndefinedVar(id=tg_id)
        public = public_list.get()
        t = time.time()
        if(product_id in public):
            public[tg_id] = t

        existing_product = product_var.get()
        
        if not existing_product:
            return JsonResponse({'error': 'Product not found'}, status=404)
        
        if str(existing_product.get('author')) != str(user_id):
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        for key, value in properties.items():
            if key in existing_product:
                existing_product[key] = value
            elif key == 'tags':
                if 'special' not in existing_product:
                    existing_product['special'] = {}
                existing_product['special']['tags'] = value
                existing_product['special']['time'] = t
        
        try:
            product_var.set(existing_product)
        except:
            try:
                product_var.cache().set(existing_product)
            except Exception as e:
                print(f"Error saving: {e}")
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        print(f"Edit error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def delete_product_view(request):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        user_data = SessionManager.validate_request(request)
        if not user_data:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        product_id = request.GET.get('id')
        if not product_id:
            return JsonResponse({'error': 'Product ID required'}, status=400)
        
        user_id = user_data.get("id")
        
        try:
            packager = Packager(id=tg.Id().from_str(product_id))
            product = packager.get_obj().get()
            if not product:
                print(f"Product {product_id} not found or is None")
        except Exception as e:
            print(f"Product {product_id} may not exist: {e}")
        
        av_data = client.get(user_id).get("avito")
        if av_data:
            try:
                product_list = tg.UndefinedVar(id=tg.Id().from_str(av_data))
                current_ids = product_list.get()
                if product_id in current_ids:
                    current_ids.remove(product_id)
                    if current_ids:
                        product_list.set(current_ids)
                    else:
                        client.update_user_info(user_id, {"avito": None})
                    public = public_list.get()
                    public.pop(product_id, None)
                    public_list.set(public)
            except Exception as e:
                print(f"Error updating user product list: {e}")
        
        try:
            packager._obj.set(None)
        except:
            pass
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        print(f"Delete error: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def get_user_products(user_id):
    av_data = client.get(user_id).get("avito")
    if not av_data:
        return []
    
    try:
        product_ids = tg.UndefinedVar(id=tg.Id().from_str(av_data)).get()
        if not product_ids:
            return []
    except Exception as e:
        print(f"Error getting product IDs: {e}")
        return []
    
    products = []
    for pid in product_ids:
        try:
            product_var = tg.UndefinedVar(id=tg.Id().from_str(pid))
            if product_var.get() is None:
                print(f"Product {pid} is None, skipping")
                continue
            
            product_data = product_var.get()
            if isinstance(product_data, dict):
                product_data['real_id'] = pid
                products.append(product_data)
            else:
                print(f"Product {pid} returned non-dict: {type(product_data)}")
        except Exception as e:
            print(f"Error loading product {pid}: {e}")
            continue
    
    return products

@csrf_exempt
def avito_dashboard(request):
    user_data = SessionManager.validate_request(request)
    if not user_data:
        return redirect('/oauth/google/')
    
    user_id = user_data['id']
    products = get_user_products(user_id)
    
    products = [p for p in products if p and isinstance(p, dict)]
    
    response = render(request, 'avito/dashboard.html', {
        'products': products,
        'name': client.get(user_id)["name"]
    })
    
    response.set_cookie('csrftoken', get_token(request), max_age=31449600, secure=True, httponly=False, samesite='Lax')
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
        'product_id': None
    })
    
    response.set_cookie('csrftoken', get_token(request), max_age=31449600, secure=True, httponly=False, samesite='Lax')
    return response

@csrf_exempt
def edit_product_page(request):
    product_id = request.GET.get('id')
    if not product_id:
        return redirect('/secmark/dashboard/')
    
    user_data = SessionManager.validate_request(request)
    if not user_data:
        return redirect('/oauth/google/')
    
    user_id = user_data['id']
    
    try:
        
        tg_id = tg.Id().from_str(product_id)
        
        var = tg.UndefinedVar(id=tg_id)
        
        product = var.get() if hasattr(var, 'get') else None
        
        if not product:
            product = var.cache().get() if hasattr(var, 'cache') else None
        
        if not product or not isinstance(product, dict):
            print(f"Product not found or invalid: {product}")
            return redirect('/secmark/dashboard/')
        
        if str(product.get('author')) != str(user_id):
            return redirect('/secmark/dashboard/')
        
    except Exception as e:
        print(f"Error loading product: {e}")
        import traceback
        traceback.print_exc()
        return redirect('/secmark/dashboard/')
    
    response = render(request, 'avito/edit_page.html', {
        'name': client.get(user_id)["name"],
        'product': product,
        'product_id': product_id
    })
    
    response.set_cookie('csrftoken', get_token(request), max_age=31449600, secure=True, httponly=False, samesite='Lax')
    return response

def avito_get_product_view(request):
    product_id = request.GET.get('id')
    try:
        id = tg.Id().from_str(product_id)
        data = tg.Var(id=id).get()
        if(type(data) == dict and set(data.keys()) >= 
           {'icon', 'name', 'price', 'description', 'backcom', 'author', 'special', 'type'}):
            return JsonResponse(data, status=200)
        else:
            return JsonResponse({"status":"Wrong ID!"})
    except Exception as e:
        print(f"Error loading product: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def avito_get_profile_ids(request):
    user_id = request.GET.get('pub_id')
    try:
        data = client.get_user_by_pub_id(user_id)
        avito = data['avito']
        if(avito is None):
            return JsonResponse({'status':'success', 
                                 'ids':[]}, status=200)
        return JsonResponse({'status':'success', 
                             'ids':tg.Var(id=avito).get()}, status=200)
    except Exception as e:
        print(f"Error loading product: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def avito_publish(request):
    product_id = request.GET.get('id')
    
    if not product_id:
        return redirect('/secmark/dashboard/')
    
    user_data = SessionManager.validate_request(request)
    if not user_data:
        return redirect('/oauth/google/')
    
    user_id = user_data['id']
    
    try:
        tg_id = tg.Id().from_str(product_id)
        var = tg.UndefinedVar(id=tg_id)
        product = var.get() if hasattr(var, 'get') else None
        
        if not product:
            product = var.cache().get() if hasattr(var, 'cache') else None
        
        if not product or not isinstance(product, dict):
            print(f"Product not found or invalid: {product}")
            return redirect('/secmark/dashboard/')
        
        if str(product.get('author')) != str(user_id):
            return redirect('/secmark/dashboard/')
            
    except Exception as e:
        print(f"Error loading product: {e}")
        import traceback
        traceback.print_exc()
        return redirect('/secmark/dashboard/')
    
    response = render(request, 'avito/publish.html', {
        'name': client.get(user_id)["name"],
        'product_id': product_id
    })
    
    response.set_cookie('csrftoken', get_token(request), max_age=31449600, secure=True, httponly=False, samesite='Lax')
    return response

@csrf_exempt
def publish_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        product_id = data.get('id')
        product_data = tg.UndefinedVar(id=tg.Id().from_str(product_id)).cache()
        print(product_id)

        public = public_list.get()
        public[product_id] = product_data.get()['special']['time']
        public_list.set(public)
        return JsonResponse({'status': 'success'}, status=200)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Error publishing product: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
    
def avito_get_public_ids(request):
    try:
        return JsonResponse({'status':'success', 
                             'ids':public_list.get()}, status=200)
    except Exception as e:
        print(f"Error loading product: {e}")
        return JsonResponse({'error': str(e)}, status=500)