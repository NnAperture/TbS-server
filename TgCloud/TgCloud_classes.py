import threading
import queue

class Id:
    def __init__(self, id:tuple|int|str, id1:None|int = None):
        '''
        ID from string|tuple|pair
        '''
        if(id1 != None):
            self.id = tuple(map(int, (id, id1)))
        elif(type(id) == tuple):
            self.id = id[:2]
        elif(type(id) == Id):
            self.id = id.id
        elif(type(id) == str):
            self.id = tuple(map(int, id.split("|")))
        else:
            self.id = tuple(id)[:2]
    
    __getitem__ = lambda self, index: self.id[index]

    __str__ = lambda self: f"{self[0]}|{self[1]}"

    __repr__ = lambda self: f'''Id:({str(self)})'''

class Output:
    def __init__(self):
        '''
        For threading functions of TgCloud.
        '''
        self.queue = queue.Queue()
        self.item = None
        self.event = threading.Event()
    
    def free(self):
        '''
        Do not use.
        '''
        self.event.set()
    
    def set_thread(self, thread):
        '''
        Do not use.
        '''
        self.thread = thread
        self.event.wait()

    def set(self, item):
        '''
        Do not use.
        '''
        self.queue.put(item)

    def check(self):
        '''
        Is function completed.
        '''
        return not self.queue.empty()

    def get(self):
        '''
        Get result of function
        Waits for end of the function
        Can be called multiple times.
        '''
        if(self.item == None):
            try:
                self.thread.join()
            except:
                pass
            self.item = self.queue.get()
            #del self.queue
        return self.item

    __repr__ = lambda self: f'''"{self.check()}"'''
    __str__ = lambda self: f'''{self.check()}'''