from django.shortcuts import render
from django.http import HttpResponse

def hello_world(request):
    """Простое представление, возвращающее 'Hello, Render!'"""
    return HttpResponse("Hello, Render!")

count = 0
def counter(request):
    global count
    if(request.method == 'GET'):
        see = request.GET.get('see')
        if(see == 'true'):
            count += 1
        return HttpResponse(str(count))
    if(request.method == 'POST'):
        see = request.POST.get('count')
        try:
            count = int(see)
        except:
            count = 0
        return HttpResponse(str(count))