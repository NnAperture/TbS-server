from TgCloud.TgCloud import *
from TgCloud import config
from django.shortcuts import render
from django.http import HttpResponse

def account(request):
    if(request.method == 'GET'):
        id = request.GET.get('id')
        return HttpResponse(read(id))
    elif(request.method == 'POST'):
        try:
            id = request.GET.get('id')
            text = request.GET.get('text')
            try:
                edit(id, text)
            except:
                new(text)
            return HttpResponse('Succesfully')
        except:
            return HttpResponse('Error')
    else:
        return HttpResponse('Hello World')