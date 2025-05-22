from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import os

# Получите токен и чат ID из переменных окружения
TELEGRAM_BOT_TOKEN = "7245976336:AAFESXVE-052DyssO-Eqd50B_D6zQTY4GaA"
TELEGRAM_CHAT_ID = -1002083840157

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise RuntimeError("Не заданы переменные окружения TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")


@csrf_exempt
def account(request):
    pass