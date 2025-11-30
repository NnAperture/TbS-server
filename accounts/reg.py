from django.http import JsonResponse
from .models import Profile
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def register_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"})

    username = request.POST.get("username")
    password = request.POST.get("password")
    email = request.POST.get("email")
    telegram_id = request.POST.get("telegram_id")

    if Profile.objects.filter(username=username).exists():
        return JsonResponse({"error": "username taken"})

    p = Profile(username=username, email=email, telegram_id=telegram_id)
    if password:
        p.set_password(password)
    p.save()

    request.session["user_id"] = p.id
    return JsonResponse({"success": True})

@csrf_exempt
def login_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"})

    username = request.POST.get("username")
    password = request.POST.get("password")

    try:
        profile = Profile.objects.get(username=username)
    except Profile.DoesNotExist:
        return JsonResponse({"error": "Неверный username или пароль"})

    if not profile.check_password(password):
        return JsonResponse({"error": "Неверный пароль"})

    request.session["user_id"] = profile.id

    return JsonResponse({"success": True})

@csrf_exempt
def me_api(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return JsonResponse({"error": "not authorized"})

    try:
        profile = Profile.objects.get(id=user_id)
    except Profile.DoesNotExist:
        return JsonResponse({"error": "not authorized"})

    return JsonResponse({
        "username": profile.username,
        "email": profile.email,
        "telegram_id": profile.telegram_id,
        "nickname": profile.nickname
    })


@csrf_exempt
def logout_api(request):
    request.session.flush()
    return JsonResponse({"success": True})

