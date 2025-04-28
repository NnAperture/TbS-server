from TgCloud.TgCloud import *
from TgCloud import config
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


async def seccion(request):
    if(request.method == "GET"):
        id = new("{}")
        return HttpResponse(str(id))