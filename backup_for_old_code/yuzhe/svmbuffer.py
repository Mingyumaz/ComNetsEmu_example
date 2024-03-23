import numpy as np
import threading

class SVMBuffer():
    def __init__(self, max_size):
        self.max_size = max_size
        self.buffer = []
        self.lock = threading.Lock()

    def init(self):
        with self.lock:
            self.buffer = []

    def clear_buffer(self):
        with self.lock:
            self.buffer = []

    def put(self, string):
        with self.lock:
            # ensure the buffer does not exceed the max size
            if len(self.buffer) < self.max_size:
                self.buffer.append(string)
            else:
                # handle the case where the buffer is full
                print("buffer is full, cannot add more string")

    # pop the first element (FIFO), to ensure the packet received is in order
    def pop(self):
        with self.lock:
            if self.buffer:
                return self.buffer.pop(0)  # remove and return the first element
            else:
                # handle the case where the buffer is empty
                return None

    def size(self):
        with self.lock:
            return len(self.buffer)