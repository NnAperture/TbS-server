from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import os
import telebot
import time

TOKEN = "7553222031:AAGS8Scd06wmktoX1qHHsMvwxCXOm-5gHCU"
bot = telebot.TeleBot(TOKEN)
adminsid = None
admintime = 0


@csrf_exempt
def report(request):
    return JsonResponse({"status": "ok"})

@csrf_exempt
def admin_check(request):
    if(request.method == "GET"):
        pass