from TgCloud.TgCloud import *
import time
import threading
from handlers import seccion

funcs = []

def delay():
    while True:
        time.sleep(86400)
        for func in funcs:
            func()

def secc_reset():
    seccion.count = 0
    seccion.id = Getkey('127.0.0.1', ram=True, pack="mes", encoding='utf-8')