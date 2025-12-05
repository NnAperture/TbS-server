from .id_class import Id
from .config import getbot, getbot_id, Bot
from .bytes_string import *
import threading
from .Bytes import Bytes
import pickle

class UndefinedVar:
    def __init__(self, value=None, id=None, convert_block=False):
        self._obj = Bytes(pickle.dumps(value), id=id, init_symbol="u", convert_block=convert_block)
    
    def get(self):
        return pickle.loads(bytes(self._obj))

    def set(self, value):
        self._obj.set(pickle.dumps(value))

    @property
    def id(self):
        return self._obj.id
    
    @id.setter
    def id(self, id):
        self._obj.id = id
    
    def __str__(self):
        return str(self.get())

    def __repr__(self):
        return f"u{self}"