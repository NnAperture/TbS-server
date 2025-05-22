from TgCloud.TgCloud import *
from TgCloud import config
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import time


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

count = 0
id = "367|67"

@csrf_exempt
def seccion(request):
    if(request.method == "GET"):
        id = new("{" + str(time.time()) + "}")
        return JsonResponse({"token":str(id)})

@csrf_exempt
def visits(request):
    global count
    if(request.method == "GET"):
        try:
            ip = get_client_ip(request)
            nw = set(Getfile(id, pack='mes', encoding='utf-8').split('|')) + {ip}
            edit(id, Getkey("|".join(nw), ram=True, encoding='utf-8'))
            response = JsonResponse({"count":(count := count + 1), "unique":len(nw)})

            response["Access-Control-Allow-Origin"] = "*"  # Разрешить запросы с любых доменов
            response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type"

            return response
        except Exception as e:
            print(e)
            return JsonResponse({"error":str(e)})
        