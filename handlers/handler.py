from TgCloud.TgCloud import *
from TgCloud import config
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def account(request):
    if(request.method == 'GET'):
        print("get")
        id = request.GET.get('id')
        print(id)
        if(id != None):
            return HttpResponse('Id is empty!')
        return HttpResponse(str(read(id)))
    elif(request.method == 'POST'):
        print("post")
        try:
            id = request.POST.get('id')
            text = request.POST.get('text')
            if(text != None and text != ""):
                try:
                    edit(id, text)
                except:
                    return HttpResponse(str(new(text)))
                return HttpResponse('Succesfully')
            else:
                return HttpResponse('Text is empty!')
        except:
            return HttpResponse('Error')
    else:
        return HttpResponse('Hello World')