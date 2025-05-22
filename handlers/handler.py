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
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are accepted.'}, status=405)

    # Предполагается, что файл приходит в поле 'file'
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    # Здесь можно изменить заголовки или метаданные, если нужно
    # Например, добавьте к названию файла или к метаданным
    filename = uploaded_file.name

    # Отправка файла в Telegram
    try:
        bot.send_document(
            chat_id=TELEGRAM_CHAT_ID,
            document=uploaded_file,
            filename=filename
        )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)