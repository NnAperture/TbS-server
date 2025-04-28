from TgCloud.TgCloud import *
from TgCloud import config
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def seccion(request):
    if(request.method == "GET"):
        print("get")
        id = new("{}")
        print(id)
        return JsonResponse({"token":str(id)})