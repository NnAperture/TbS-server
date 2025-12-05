from .id_class import Id
from .config import getbot, getbot_id, Bot
from .bytes_string import *
import threading
from queue import Queue
from .List import List
from .Undefined import UndefinedVar
from .chain import Chain
from .Var import Var

BASE_ALLOC = 5
_UNSET = object()

class Dict:
    def __init__(self, value=None, id=None, *, cache_pages=0, cache_items=0, block_cache=0):
        self.evt = threading.Event()
        self.lock = threading.RLock()

        self.cache_pages = cache_pages
        self.cache_items = cache_items
        self._block_cache = {}
        self._block_max = block_cache

        self._header = None

        if(id == None):
            threading.Thread(target=self.upload).start()
        else:
            threading.Thread(target=self.download, args=(id, )).start()
        if(value != None):
            self.extend(value)
    
    def _wait_init(self):
        self.evt.wait()

    def extend(self, dict):
        def th(self=self, dict=dict):
            with self.lock:
                temp = {}
                for key in dict:
                    hashk = hash(key)
                    index = hashk // self.alloc
                    temp.setdefault(index, []).append((key, dict[key]))
                
                for index in temp:
                    block = self._get_block(index)
                    new = block.get() | {k:v for k, v in temp[index]}
                    block.set(new)
        threading.Thread(target=th).start()
    
    def __setitem__(self, key, value):
        self._wait_init()
        hashk = hash(key)
        index = hashk % self.alloc
        value = Var(value)
        def th(self=self, index=index, value=value, key=key):
            with self.lock:
                block = self._get_block(index)
                new = block.get() | {key:str(value.id)}
                block.set(new)
        threading.Thread(target=th).start()
    
    def __getitem__(self, key):
        return self.get(key, KeyError(f"key {key}"))

    def _get(self):
        self._wait_init()
        return dict((key, self[key]) for key in self)

    def __iter__(self):
        with self.lock:
            for block in self._list:
                for key in block.get():
                    yield key

    def get(self, key=_UNSET, default=None):
        if(key is _UNSET):
            return self._get()
        self._wait_init()
        hashk = hash(key)
        index = hashk % self.alloc
        def th(id:Id, self=self, index=index, key=key):
            with self.lock:
                block = self._get_block(index)
                try:
                    id.set(block.get()[key])
                except KeyError:
                    id.set(UndefinedVar(default).id)
        return Var(id=Id(func=th))
    
    def _get_block(self, index):
        if(index in self._block_cache):
            try:
                v:Var = self._block_cache[index]
                v._wait_init()
                return v._obj
            except: pass
        block:Var = self._list[index]
        v._wait_init()
        block._obj._obj._obj.convert_block = True
        self._block_cache[index] = block
        threading.Thread(target=self.gc).start()
        return block._obj

    def upload(self):
        with self.lock:
            if(self._header is None):
                self._list = List([UndefinedVar({}, convert_block=True) for _ in range(BASE_ALLOC)], cache_pages=self.cache_pages)
                self.alloc = BASE_ALLOC
                self.true_size = 0
            
            st = str({"list":self._list.id,
                    "alloc":self.alloc,
                    "true_size":0,
                    "cache":None,
                    "overflow_index":0})
            
            if(self._header is None):
                self._header = Chain(st, init="d")
            else:
                self._header.set(st)
            self.evt.set()

    def download(self, id=None):
        with self.lock:
            if(not id is None):
                self._header = Chain(id=id, init="d")
            
            dic = eval(self._header.get())
            self._list = List(id=dic["list"])
            self.alloc = dic["alloc"]
            self.true_size = dic["true_size"]
            self.overflow_index = dic["overflow_index"]
            self._block_cache = {}
            self.evt.set()
            print(self._list)
    
    def gc(self):
        with self.lock:
            while(len(self._block_cache) > self._block_max):
                self._block_cache.pop(next(self._block_cache.__iter__()))
    
    def __str__(self):
        return str(self.get())

    def __repr__(self):
        return f"d{self}"

    @property
    def id(self):
        with self.lock:
            return self._header.id