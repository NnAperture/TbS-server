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

@csrf_exempt
def admin_check(request):
    global current_code, code_timestamp
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST required"}, status=400)
    data = request.POST
    code = data.get("code")
    if not code:
        return JsonResponse({"status": "error", "message": "Code missing"}, status=400)

    code_hash = hashlib.sha256(code.encode()).hexdigest()

    if code_hash != ADMIN_HASH:
        return JsonResponse({"status": "error", "message": "Invalid code"}, status=403)
    now = time.time()
    if not current_code or now - code_timestamp > 3600:
        current_code = "{:05d}".format(random.randint(0, 99999))
        code_timestamp = now
        bot.send_message(ID, f"Ваш код: `{current_code}`", parse_mode="MARKDOWN")
    print(current_code)

    return JsonResponse({"status": "ok"})

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
    print(current_code, five_digit)

    if not code or not five_digit:
        return JsonResponse({"status": "error", "message": "Missing parameters"}, status=400)

    code_hash = hashlib.md5(code.encode()).hexdigest()

    now = time.time()
    print(code_hash == ADMIN_HASH, current_code == five_digit, now - code_timestamp <= 3600)
    if code_hash == ADMIN_HASH and current_code == five_digit and now - code_timestamp <= 3600:
        return JsonResponse({"status": True})
    else:
        return JsonResponse({"status": [False, code_hash == ADMIN_HASH, current_code == five_digit, now - code_timestamp <= 3600]})
