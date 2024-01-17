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
            # Ensure the buffer does not exceed the max size
            if len(self.buffer) < self.max_size:
                self.buffer.append(string)
            else:
                # Optional: Handle the case where the buffer is full
                print("Buffer is full, cannot add new string")

    def pop(self):
        with self.lock:
            if self.buffer:
                return self.buffer.pop(0)  # Remove and return the first element
            else:
                # Optional: Handle the case where the buffer is empty
                return None

    def size(self):
        with self.lock:
            return len(self.buffer)