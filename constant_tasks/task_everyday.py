import time
import threading
from handlers import seccion

funcs = []

def delay():
    while True:
        time.sleep(86400)
        for func in funcs:
            func()
