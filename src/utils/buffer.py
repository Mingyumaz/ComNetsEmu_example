import numpy as np
import threading
import copy


class Buffer():
    def __init__(self):
        self.length = 0
        self.buffer = bytes()
        self.lock = threading.Lock()

    def init(self):
        self.lock.acquire()
        # print(f"*** [log]: buffer init !")
        self.length = 0
        self.buffer = bytes()
        self.lock.release()

    def clear_buffer(self):
        self.lock.acquire()
        # print(f"*** [log]: buffer clear !")
        self.length = 0
        self.buffer = bytes()
        self.lock.release()

    def put(self, x:bytes):
        self.lock.acquire()
        # _size = self.length + x.shape[1]
        self.buffer += x
        self.length = len(self.buffer)
        self.lock.release()

    def extract(self):
        self.lock.acquire()
        # print(f"*** [log]: buffer length = {len(self.buffer)}")
        out = copy.deepcopy(self.buffer)
        self.lock.release()
        # print(f"*** [log]: buffer extract length {len(out)}")
        return out

    def extract_n(self, n):
        self.lock.acquire()
        out = copy.deepcopy(self.buffer[0:int(n)])
        self.lock.release()
        return out
    
    def atomic_put_last(self, x:bytes):
        self.lock.acquire()
        self.buffer += x
        self.length = len(self.buffer)
        out = copy.deepcopy(self.buffer)
        self.buffer = bytes()
        self.length = 0
        self.lock.release()
        return out

    def acquire(self):
        self.lock.acquire()

    def release(self):
        self.lock.release()

    def size(self):
        return self.length