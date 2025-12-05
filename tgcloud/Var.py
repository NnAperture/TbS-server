from .List import List
from .Int import Int
from .String import Str
from .Null import Null
from .Bytes import Bytes
from .id_class import Id
from .Undefined import UndefinedVar
from .config import getbot_id
import threading
import gc

_UNSET = object()  # внутренний маркер для "аргумент не передан"


class Var:
    def __init__(self, value=_UNSET, id=None):
        object.__setattr__(self, "lock", threading.RLock())
        object.__setattr__(self, "_obj", None)
        object.__setattr__(self, "_init_done", threading.Event())
        object.__setattr__(self, "_init_thread_id", None)
        def th(self=self, value=value, id=id):
            object.__setattr__(self, "_init_thread_id", threading.get_ident())
            if(type(value) == Var):
                self._obj = value._obj
            if id is not None:
                id = Id(id)

                if value is _UNSET:
                    text = getbot_id(id).get_text(id) or ""
                    text = text.strip()

                    if text.startswith("i"):
                        self._obj = Int(id=id)
                    elif text.startswith("s"):
                        self._obj = Str(id=id)
                    elif text.startswith("L"):
                        self._obj = List(id=id)
                    elif text.startswith("b"):
                        self._obj = Bytes(id=id)
                    elif text.startswith("n"):
                        self._obj = Null(id=id)
                    elif text.startswith("u"):
                        self._obj = UndefinedVar(id=id)
                else:
                    wrapped = self._wrap_value(value, id)
                    wrapped._id = id
                    self._obj = wrapped
            else:
                if value is _UNSET:
                    self._obj = Null()
                else:
                    self._obj = self._wrap_value(value)
            self._init_done.set()
        threading.Thread(target=th).start()
        gc.collect()

    def _allowed(self):
        cur = threading.get_ident()
        init_thread = object.__getattribute__(self, "_init_thread_id")
        done = object.__getattribute__(self, "_init_done")
        if cur == init_thread:
            return True
        if done.is_set():
            return True
        return False
    
    def _wait_init(self):
        if not self._allowed():
            self._init_done.wait()

    def _wrap_value(self, value, id=None):
        if isinstance(value, (Str, Int, List, Null, Bytes, UndefinedVar)):
            return value
        
        elif isinstance(value, bytes):
            return Bytes(value, id=id)
        elif isinstance(value, str):
            return Str(value, id=id)
        elif isinstance(value, int):
            return Int(value, id=id)
        elif isinstance(value, (list, tuple)):
            return List(value, id=id)
        elif value is None:
            return Null(id=id)
        else:
            return UndefinedVar(value, id=id)

    def set(self, value):
        self._wait_init()
        def th(self=self, value=value):
            with self.lock:
                new_obj = self._wrap_value(value)
                new_obj._id = getattr(self._obj, "_id", None)
                self._obj = new_obj
        threading.Thread(target=th).start()

    def get(self):
        self._wait_init()
        with self.lock:
            if hasattr(self._obj, "get"):
                return self._obj.get()
            return self._obj

    def __getattribute__(self, name):
        if name in {
            "_wait_init", "_allowed",
            "_init_done", "_init_thread_id",
            "lock", "_obj",
            "__dict__", "__class__", "_wrap_value"
        }:
            return object.__getattribute__(self, name)
        self._wait_init()
        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        if name in {
            "_init_done", "_init_thread_id",
            "lock", "_obj",
            "__dict__", "__class__"
        }:
            return object.__setattr__(self, name, value)
        self._wait_init()
        return object.__setattr__(self, name, value)

    def __getitem__(self, key):
        with self.lock:
            if hasattr(self._obj, "__getitem__"):
                return self._obj[key]
            raise TypeError(f"{type(self._obj).__name__} does not support indexing")

    def __setitem__(self, key, value):
        with self.lock:
            if hasattr(self._obj, "__setitem__"):
                self._obj[key] = value
                return
            raise TypeError(f"{type(self._obj).__name__} does not support item assignment")

    def __add__(self, other):
        self._init_done.wait()
        with self.lock:
            if hasattr(self._obj, "__add__"):
                return Var(self._obj + (other._obj if isinstance(other, Var) else other))
            raise TypeError(f"{type(self._obj).__name__} does not support addition")

    def __iadd__(self, other):
        self._init_done.wait()
        with self.lock:
            if hasattr(self._obj, "__iadd__"):
                self._obj += (other._obj if isinstance(other, Var) else other)
                return self
            raise TypeError(f"{type(self._obj).__name__} does not support addition")

    def __sub__(self, other):
        self._init_done.wait()
        with self.lock:
            if hasattr(self._obj, "__sub__"):
                return Var(self._obj - (other._obj if isinstance(other, Var) else other))
            raise TypeError(f"{type(self._obj).__name__} does not support subtraction")

    def __isub__(self, other):
        self._init_done.wait()
        with self.lock:
            if hasattr(self._obj, "__isub__"):
                self._obj -= (other._obj if isinstance(other, Var) else other)
                return self
            raise TypeError(f"{type(self._obj).__name__} does not support subtraction")

    def __int__(self):
        self._init_done.wait()
        with self.lock:
            if hasattr(self._obj, "__int__"):
                return int(self._obj)
            raise TypeError("Cannot convert Var to int")

    def __len__(self):
        self._init_done.wait()
        with self.lock:
            if hasattr(self._obj, "__len__"):
                return len(self._obj)
            raise TypeError("Object has no length")

    def __repr__(self):
        self._init_done.wait()
        with self.lock:
            return f"<Var {repr(self._obj)}>"

    def __str__(self):
        self._init_done.wait()
        with self.lock:
            return str(self._obj)

    def __int__(self):
        self._init_done.wait()
        with self.lock:
            return int(self._obj)
    
    def __bytes__(self):
        self._init_done.wait()
        with self.lock:
            return bytes(self._obj)

    def __iter__(self):
        self._init_done.wait()
        with self.lock:
            for el in self._obj:
                yield el

    @property
    def id(self):
        self._init_done.wait()
        with self.lock:
            return self._obj.id

    @id.setter
    def id(self, value):
        self._init_done.wait()
        with self.lock:
            self._obj._id = Id(value)
            self._obj.download()
