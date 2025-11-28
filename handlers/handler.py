from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import telebot
import time
import hashlib
import random

TOKEN = "7553222031:AAGS8Scd06wmktoX1qHHsMvwxCXOm-5gHCU"
ID = -1003455538639

bot = telebot.TeleBot(TOKEN)

ADMIN_HASH = "a98274576b946144c05dbe7041055c0acc9783da91e101e30341c95fad90811c"

current_code = None
code_timestamp = 0

news = ""
@csrf_exempt
def update_news(request):
    if request.method == "POST":
        data = request.POST
        code = data.get("code")
        five_digit = data.get("five_digit")
        if validate_code(code, five_digit):
            global news
            news = data.get("content")

            import requests
            try:
                resp = requests.get("http://k90908k8.beget.tech/news/update.php")
                print("PHP response:", resp.text)
            except Exception as e:
                print("PHP request error:", e)
            return JsonResponse({"status": "ok", "c": news})
        else:
            return JsonResponse({"status": "error", "message": "Wrong code"})
    return JsonResponse({"status": "error", "message": "POST required"})


@csrf_exempt
def check_code(request):
    global current_code, code_timestamp

    if request.method == "POST":
        data = request.POST
    elif request.method == "GET":
        data = request.GET
    else:
        return JsonResponse({"status": "error", "message": "GET or POST required"}, status=400)

    code = data.get("code")
    five_digit = data.get("five_digit")

    if not code or not five_digit:
        return JsonResponse({"status": "error", "message": "Missing parameters"}, status=400)

    code_hash = hashlib.sha256(code.encode()).hexdigest()

    now = time.time()
    if code_hash == ADMIN_HASH and current_code == five_digit and now - code_timestamp <= 3600:
        return JsonResponse({"status": True})
    else:
        return JsonResponse({"status": False})

def validate_code(code, five_digit):
    if not code or not five_digit:
        return False

    code_hash = hashlib.sha256(code.encode()).hexdigest()
    now = time.time()
    return code_hash == ADMIN_HASH and current_code == five_digit and now - code_timestamp <= 3600


news = ""
@csrf_exempt
def update_news(request):
    if request.method == "POST":
        data = request.POST
        code = data.get("code")
        five_digit = data.get("five_digit")

        if validate_code(code, five_digit):
            global news
            news = data.get("content")
            return JsonResponse({"status": "ok", "c": news})
        else:
            return JsonResponse({"status": "error", "message": "Wrong code"})

    return JsonResponse({"status": "error", "message": "POST required"})


@csrf_exempt
def get_news(request):
    if request.method == "GET":
        global news
        if(news != ""):
            n, news = news, None
            return JsonResponse({"status": "ok", "content":news})
        else:
            return JsonResponse({"status": "error", "message": "News empty"})

    return JsonResponse({"status": "error", "message": "POST required"})
