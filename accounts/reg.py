import json
import random
import string
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings

PHP_API_URL = settings.PHP_API_URL

# временное хранилище SID
sessions = {}


# ======= ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ =========

def generate_sid():
    return "SID_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))


# ========= СТАРТ СОЗДАНИЯ АККАУНТА =========
@csrf_exempt
def start_create_account_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "method must be POST"}, status=400)

    login = request.POST.get("login")
    password = request.POST.get("password")
    email = request.POST.get("email")
    telegram_id = request.POST.get("telegram_id")
    body_link = request.POST.get("body_link")

    # нужны хотя бы login и хотя бы один из остальных контактов
    if not login:
        return JsonResponse({"error": "login_required"}, status=400)

    if not (password or email or telegram_id):
        return JsonResponse({"error": "need_at_least_one_contact"}, status=400)

    sid = generate_sid()

    sessions[sid] = {
        "timestamp": timezone.now(),
        "confirmed": False,
        "user_data": {
            "login": login,
            "password": password,
            "email": email,
            "telegram_id": telegram_id,
            "body_link": body_link,
        },
        "telegram_pending_code": None,
        "telegram_id": None  # чтобы хранить временный id от бота
    }

    return JsonResponse({"sid": sid})
    

# ========= ПОЛУЧЕНИЕ ДАННЫХ ПО SID =========
@csrf_exempt
def get_user_data_api(request):
    sid = request.GET.get("sid")
    if sid not in sessions:
        return JsonResponse({"error": "invalid_sid"}, status=400)

    return JsonResponse({
        "sid": sid,
        "data": sessions[sid]
    })


# ========= ТЕЛЕГРАМ: БОТ ОТПРАВИЛ КОД =========
@csrf_exempt
def telegram_send_code_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "method must be POST"}, status=400)

    sid = request.POST.get("sid")
    code = request.POST.get("code")
    telegram_id = request.POST.get("telegram_id")

    if not sid or not code or not telegram_id:
        return JsonResponse({"error": "missing_parameters"}, status=400)

    if sid not in sessions:
        return JsonResponse({"error": "invalid_sid"}, status=400)

    sessions[sid]["telegram_pending_code"] = code
    sessions[sid]["telegram_id"] = telegram_id

    return JsonResponse({"status": "code_saved"})


# ========= ТЕЛЕГРАМ: ПОЛЬЗОВАТЕЛЬ ВВОДИТ КОД =========
@csrf_exempt
def telegram_verify_code_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "method must be POST"}, status=400)

    sid = request.POST.get("sid")
    code = request.POST.get("code")

    if sid not in sessions:
        return JsonResponse({"error": "invalid_sid"}, status=400)

    stored_code = sessions[sid]["telegram_pending_code"]
    stored_tg_id = sessions[sid]["telegram_id"]

    if not stored_code:
        return JsonResponse({"error": "no_code_pending"}, status=400)

    if code != stored_code:
        return JsonResponse({"error": "wrong_code"}, status=403)

    # подтверждение
    sessions[sid]["confirmed"] = True
    sessions[sid]["user_data"]["telegram_id"] = stored_tg_id

    return JsonResponse({"status": "telegram_confirmed"})


# ========= ФИНАЛЬНОЕ СОЗДАНИЕ АККАУНТА (PHP API) =========
@csrf_exempt
def complete_account_creation_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "method must be POST"}, status=400)

    sid = request.POST.get("sid")
    if sid not in sessions:
        return JsonResponse({"error": "invalid_sid"}, status=400)

    user = sessions[sid]["user_data"]

    # запрос к php API
    try:
        r = requests.post(
            PHP_API_URL + "/create_user.php",
            data=user,
            timeout=10
        )
    except Exception as e:
        return JsonResponse({"error": "php_api_error", "details": str(e)}, status=500)

    return JsonResponse({
        "status": "account_created",
        "php_response": r.text
    })
