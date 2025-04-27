import telebot
import threading
import time
import random
from TgCloud.TgCloud_classes import *
import TgCloud.TgCloud_classes as tgcc
import sys
import zipfile
import os
import json
import queue

class Tunnel:
    def __init__(self, power=1):
        self.power = power
        self.input = [new("-") for i in range(power)]
        self.output = [new("-") for i in range(power)]
        self.id = new(f'''{power}:{".".join(map(str, self.input))}:{".".join(map(str, self.output))}''')
        self.pointer = 0
    
    def accept(self, function, timeout=-1, delay=0.3):
        '''Waits for requests and gives it to your function.
        '''
        start = time.time()
        while(read(self.input[self.pointer]) == "-" and (timeout == -1 or time.time() - start < 3)):
            time.sleep(delay)
        r = read(self.input[self.pointer])
        uni_start_thread(edit, args=(self.output[self.pointer], str(function(r))))
        edit(self.input[self.pointer], '-')
        self.pointer += 1
        if(self.pointer == self.power):
            self.pointer = 0

class Router:
    def __init__(self, delay=5):
        self.input = new('Input')
        self.output = new('Output')
        self.readed = new('Readed')
        self.id = new(f"Router_base:{self.input}:{self.output}:{self.readed}")
        self.tunnels = queue.Queue()
        self.delay = delay
    
    def get_id(self):
        return self.id
    
    def route(self):
        a = read(self.input)
        clients = a.split(":")[1:]
        if(clients != []):
            edit(self.input, 'Input')
            output = []
            for t in clients:
                tmp = t.split("-")
                t, pwr = tmp

                tunnel = Tunnel(int(pwr))
                self.tunnels.put(tunnel)
                output.append(f"{t}-{tunnel.id}")

            edit(self.output, read(self.output) + f''':{":".join(output)}''')
        readers = read(self.readed).split(":")[1:]
        if(readers != []):
            edit(self.readed, "Readed")
            new_out = read(self.output).split(":")[1:]
            for r in readers:
                for out in new_out:
                    if(r in out):
                        break
                if(r in out):
                    new_out.remove(out)
            edit(self.output, "Output" + "".join([":" + i for i in new_out]))
    
    def router(self):
        while True:
            self.route()
            time.sleep(self.delay)
    
    def router_thread(self):
        uni_start_thread(self.router)
    
    def accept_tunnel(self) -> Tunnel:
        while(self.tunnels.empty()):
            time.sleep(0.3)
        return self.tunnels.get()

class Client:
    def __init__(self, ID_router, power=1, timeout=-1):
        r_inp, r_out, r_read = read(ID_router).split(":")[1:]

        uniq = str(time.time())
        req = f":{uniq}-{power}"
        while(req not in read(r_inp)):
            edit(r_inp, read(r_inp) + req)
        
        start_time = time.time()
        while(timeout == -1 or time.time() - start_time < timeout):
            time.sleep(0.5)
            r = read(r_out)
            if(uniq in r):
                break
        if(uniq in r):
            self.success = True

            for out in r.split(":")[1:]:
                if(uniq in out):
                    break
            self.tunnel = out.split("-")[1]
            self.pointer = 0
            self.power, self.requests, self.answer = read(self.tunnel).split(":")
            self.requests, self.answer = self.requests.split("."), self.answer.split(".")

            req = f":{uniq}"
            while(req not in read(r_read)):
                edit(r_read, read(r_read) + req)
        else:
            self.success = False
    
    def request(self, message, timeout=-1, delay=0.3):
        edit(self.requests[self.pointer], message)
        start = time.time()
        r = read(self.answer[self.pointer])
        while(r == "-" and (timeout == -1 or time.time() - start < 3)):
            time.sleep(delay)
            r = read(self.answer[self.pointer])
        uni_start_thread(edit, args=(self.answer[self.pointer], '-'))
        self.pointer += 1
        if(self.pointer == self.power):
            self.pointer = 0
        return r

class zip:
    '''
    Part to work with ZIP archive. Just useful.
    '''
    def create(folder_path, output_path):
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arcname)

    def extract(archive_path, output_path):
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(output_path)

    def rmmdir(folder):
        for root, dirs, files in os.walk(folder):
            for file in files:
                file_path = os.path.join(root, file)
                os.remove(file_path)
        for root, dirs, files in os.walk(folder):
            for file in dirs:
                file_path = os.path.join(root, file)
                os.rmdir(file_path)
        try:
            os.rmdir(folder)
        except:
            pass

def start_th(comand, *, args:tuple = (), kwards:dict = {}) -> Output:
    if(type(args) != tuple):
        args = (args, )
    out = Output()
    app = {"output" : out}
    th = threading.Thread(target = comand, args=args, kwargs=app | kwards)
    th.start()
    out.set_thread(th)
    return out

def uni_start_thread(comand, *, args:tuple=(), kwards:dict={}) -> threading.Thread:
    th = threading.Thread(target=comand, args=args, kwargs=kwards, daemon=True)
    th.start()
    return th
def bot_bot(ind):
    return ind % len(group)

def group_bot(ind):
    return group[ind // (len(bots) // len(group))]

def forward(idd):
    return bots[idd[1]].bot.forward_message(trash, group_bot(idd[1]), idd[0])

class Bot:
    __str__ = lambda self: f"{self.bot}, {self.group}"
    def __init__(self, bot, group, ind):
        self.ind = ind
        self.bot, self.group = bot, group
    
    def send_message(self, text):
        return self.bot.send_message(self.group, text, timeout=1000).id
    
    def send_document(self, contain):
        return self.bot.send_document(self.group, contain, timeout=1000).id
    
    def edit_message(self, idd, text):
        return self.bot.edit_message_text(text, chat_id=self.group, message_id=idd)


choosebot = lambda: random.randint(0, len(bots) - 1)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

bots:list[Bot] = []
sheet, group, trash, edites = None, None, None, None

def cr_edites():
    a = []
    for i in range(len(bots)):
        a.append((bots[i].send_message(str(time.time())), i))
    return tuple(a)

def config(conf):
    global sheet
    global bots
    global group
    global trash
    config = conf

    def edts(e):
        global edites
        edites = tuple(Id(i) for i in config['edites'])
    edts(config['edites'])
    i = 0
    for gr in config['groups']:
        for tok in config['tokens']:
            bot = telebot.TeleBot(tok)
            bots.append(Bot(bot, gr, i))
            i += 1
    group = config['groups']
    trash = config['trashgroup']
    if(config['edites'] == () or len(config['edites']) != len(bots)):
        print("TgCloud: TAKE YOUR EDITIES", cr_edites(), sep="\n")
        sys.exit()

def read(id:Id, *, output:Output=None):
    '''
    Read variable by id.
    Output: None - linear return; class<Output> - Threading, result into class
    '''
    if(output == None):
        id = Id(id)
        return forward(id).text
    else:
        def body(id=id, output=output):
            id = Id(id)
            output.set(forward(id).text)
        thread = threading.Thread(target=body)
        thread.start()
        output.free()

def edit(id:Id|str, text, *, cooldown:bool=True, output:Output|None=None):
    '''
    Edites value of variable by ID (id can be string or class Id).
    Output: None - linear return; class<Output> - Threading, result into class
    '''
    def body(id=id, text=str(text), cooldown=cooldown):
        id = Id(id)
        
        if(cooldown):
            while time.time() - float(read(edites[id[1]])) < 6:
                time.sleep(0.8)
            try:
                bots[id[1]].edit_message(id[0], text)
            except Exception as a:
                print(a)
            bots[id[1]].edit_message(edites[id[1]], time.time())
        else:
            b = True
            while(b):
                try:
                    bots[id[1]].edit_message(id[0], text)
                    b = False
                except Exception as a:
                    if "Bad Request: message is not modified" in str(a):
                        return
                time.sleep(0.1)
        if(output != None):
            output.set(None)
    
    if(output != None):
        output.free()
    body()

def new(text:str="var", *, output:Output|None=None):
    '''
    Creates new variable.
    text - start value of variable.
    Output: None - linear return; class<Output> - Threading, result into class

    Returns ID.
    '''
    def base(text=text):
        while 1:
            try:
                bot = choosebot()
                return Id(bots[bot].send_message(text), bot)
            except Exception as a:
                    print(a)
    
    def body(output=output):
        output.set(base())
    
    if(output == None):
        return base()
    else:
        thread = threading.Thread(target=body)
        thread.start()
        output.free()

def Getkey(content:str|bytes = "", *, ram:bool = False, output:Output|None = None, th:bool=False, pack:str="", encoding=""):
    '''
    If ram, will upload content like containment of file
    else from file with path=content

    Uploads a file and returns key for uploading.
    th - faster way to upload, but can use up to 200mb of RAM.
    pack - way to upload key to make key to 1 id. Can be "" (returns full key), "mes" (or id in (1|1) type. faster way, maximum size of key - 4000 symbols), "file" (can use more than 1 ID, if key is more than 20mb.)
    encoding - encodes content from string to bytes (only if RAM).
    Output: None - linear return; class<Output> - Threading, result into class
    '''
    if(encoding != ""):
        content = content.encode(encoding)

    def upl_pocket(pocket):
        while 1:
            try:
                bot = choosebot()
                return Id(bots[bot].send_document(pocket), bot)
            except Exception as a:
                print(a)

    def th_upl_pocket(pocket, *, output:Output=None):
        output.free()
        while 1:
            try:
                bot = choosebot()
                output.set(Id(bots[bot].send_document(pocket), bot))
                return
            except Exception as a:
                print(a)

    def standart(content=content, ram=ram, pack=pack):
        if(not ram):
            file = open(content, "rb")

            ids = []
            pocket = file.read(19800000)
            while pocket:
                ids.append(upl_pocket(pocket))
                pocket = file.read(19800000)

            file.close()

            if("|" in pack or type(pack) == Id):
                key = "=".join(map(str, ids))
                edit(pack, key)
                return Id(pack)
            elif(pack == "mes"):
                key = "=".join(map(str, ids))
                return new(key),
            elif(pack == "file"):
                key = "=".join(map(str, ids))
                return Getkey(key, ram=True, encoding="utf-8")
            else:
                return ids
        else:
            ids = []
            pocket, content = content[:19800000], content[19800000:]
            while pocket:
                ids.append(upl_pocket(pocket))
                pocket, content = content[:19800000], content[19800000:]
            
            if("|" in pack or type(pack) == Id):
                key = "=".join(map(str, ids))
                edit(pack, key)
                return Id(pack)
            elif(pack == "mes"):
                key = "=".join(map(str, ids))
                return new(key),
            elif(pack == "file"):
                key = "=".join(map(str, ids))
                return Getkey(key, ram=True, encoding="utf-8")
            else:
                return ids

    def thread(content=content, ram=ram, pack=pack):
        if(not ram):
            file = open(content, "rb")
            ids = []
            pocket = file.read(19800000)
            output:list[Output] = []
            i = 0
            while i < 10 and pocket:
                output.append(start_th(th_upl_pocket, args=(pocket, )))
                pocket = file.read(19800000)
                i += 1
            while pocket:
                ids.append(output[0].get())
                output.pop(0)
                output.append(start_th(th_upl_pocket, args=(pocket, )))
                pocket = file.read(19800000)
            for out in output:
                ids.append(output[0].get())
                output.pop(0)
            file.close()
            
            if("|" in pack or type(pack) == Id):
                key = "=".join(map(str, ids))
                edit(pack, key)
                return Id(pack)
            elif(pack == "mes"):
                key = "=".join(map(str, ids))
                return new(key),
            elif(pack == "file"):
                key = "=".join(map(str, ids))
                return Getkey(key, ram=True, encoding="utf-8")
            else:
                return ids
        else:
            ids = []
            pocket, content = content[:19800000], content[19800000:]
            output:list[Output] = []
            i = 0
            while i < 10 and pocket:
                output.append(start_th(th_upl_pocket, args=pocket))
                i += 1
                pocket, content = content[:19800000], content[19800000:]
            while pocket:
                ids.append(output[0].get())
                output.pop(0)
                output.append(start_th(th_upl_pocket, args=pocket))
                i += 1
                pocket, content = content[:19800000], content[19800000:]
            for out in output:
                ids.append(out.get())
            
            if("|" in pack or type(pack) == Id):
                key = "=".join(map(str, ids))
                edit(pack, key)
                return Id(pack)
            elif(pack == "mes"):
                key = "=".join(map(str, ids))
                return new(key),
            elif(pack == "file"):
                key = "=".join(map(str, ids))
                return Getkey(key, ram=True, encoding="utf-8")
            else:
                return ids

    if(output == None):
        if(not th):
            return "=".join(map(str, standart()))
        else:
            return "=".join(map(str, thread()))
    else:
        output.free()
        if(not th):
            start_th(lambda output=output:output.set("=".join(map(str, standart()))))
        else:
            start_th(lambda output=output:output.set("=".join(map(str, thread()))))

def Getfile(key:str="", *, path:str|None=None, output:Output|None=None, th:bool=True, pack:str="", encoding=""):
    '''
    if path == None, downloads to RAM and returns result.
    Downloads a file from key.
    pack == pack when uploaded
    th - faster downloading but can use up to 200 mb of RAM
    encoding - if != "", decodes output (only if RAM)
    Output: None - linear return; class<Output> - Threading, result into class
    '''
    def getpocket(id):
        file_id_info = bots[id[1]].bot.get_file(forward(id).document.file_id)
        return bots[id[1]].bot.download_file(file_id_info.file_path)

    def getpocket_th(id, *, output:Output):
        output.free()
        file_id_info = bots[id[1]].bot.get_file(forward(id).document.file_id)
        output.set(bots[id[1]].bot.download_file(file_id_info.file_path))

    def standart(key=key, path=path, pack=pack, encoding=encoding):
        if(pack == "mes"):
            key = read(key)
        elif(pack == "file"):
            key = Getfile(key, encoding="utf-8")
        if(path != None):
            file = open(path, 'wb')
            for id in key.split("="):
                file.write(getpocket(Id(id)))
            file.close()
        else:
            out = bytes()
            for id in key.split("="):
                out += getpocket(Id(id))
            if(encoding == ""):
                return out
            else:
                return out.decode(encoding)
    
    def thread(key=key, path=path, pack=pack, encoding=encoding):
        if(pack == "mes"):
            key = read(key)
        elif(pack == "file"):
            key = Getfile(key, encoding="utf-8")
        if(path != None):
            file = open(path, "wb")
            i = 0
            ids = tuple(map(Id, key.split("=")))
            output:list[Output] = []
            while i < 10 and i < len(ids):
                output.append(start_th(getpocket_th, args=(ids[i],)))
                i += 1
            
            for i in range(10, len(ids)):
                file.write(output[0].get())
                output.pop(0)
                output.append(start_th(getpocket_th, args=(ids[i],)))
            for out in output:
                file.write(out.get())
            file.close()
        else:
            out = bytes()
            output:list[Output] = []
            for id in key.split("="):
                output.append(start_th(getpocket_th, args=(Id(id),)))
            for output in output:
                out += output.get()
                del output
            if(encoding == ""):
                return out
            else:
                return out.decode(encoding)

    if(output == None):
        if(not th):
            return standart()
        else:
            return thread()
    else:
        output.free()
        if(not th):
            uni_start_thread(lambda output1=output, standart=standart:output1.set(standart()))
        else:
            uni_start_thread(lambda output1=output, thread=thread:output1.set(thread()))