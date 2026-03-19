from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest, JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt, csrf_protect
from django.middleware.csrf import get_token, rotate_token
from django.conf import settings
from django.urls import reverse
import requests
import tgcloud as tg
from .client import client
from .reg import SessionManager

