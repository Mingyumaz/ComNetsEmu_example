import threading
import copy

class DictBuffer():
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

    def put(self, dict_data):
        with self.lock:
            if len(self.buffer) < self.max_size:
                self.buffer.append(copy.deepcopy(dict_data))  # 使用深拷贝来添加字典
            else:
                print("Buffer is full, cannot add new dict")

    def pop(self):
        with self.lock:
            if self.buffer:
                return self.buffer.pop(0)  # 移除并返回第一个元素
            else:
                return None
    
    def pop_n(self, n):
        # pop out n items from the buffer
        with self.lock:
            items_to_return = []
            for _ in range(min(n, len(self.buffer))):
                items_to_return.append(self.buffer.pop(0))
            return items_to_return
    
    def size(self):
        with self.lock:
            return len(self.buffer)
