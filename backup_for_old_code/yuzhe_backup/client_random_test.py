# 发送随机数据包到服务器，测试链路是否正确，以及能否处理数据包

import time
import argparse
from simpleemu.simpleudp import simpleudp
from utils.log import *
from utils.packet import *
import time

# parse args
parser = argparse.ArgumentParser(description="Using TCP or UDP")
parser.add_argument("--protocol", "-p", type=str, choices=["tcp", "udp", "t", "u"], default="udp",
                    help="choosing protocol, tcp/t or udp/u(default udp).")
args = parser.parse_args()

# tcp/udp
if args.protocol in ["udp", "u"]:
    protocol = "udp"
    simple = simpleudp

# network setting
ifce_name, node_ip = simple.get_local_ifce_ip('10.0')

# app = SimpleCOIN(ifce_name=ifce_name, n_func_process=5, lightweight_mode=True)
serverAddressPort = ("10.0.0.30", 9999)
clientAddressPort = ("10.0.0.10", 9999)

start_time = time.time()

def generate_bytes_list(n, m):
    """
    生成一个包含n个元素的列表，每个元素是长度为m的随机字节。

    参数:
    - n: 列表中元素的数量
    - m: 每个字节串的长度

    返回值:
    - 一个包含n个长度为m的随机字节的列表
    """
    return [os.urandom(m) for _ in range(n)]

def generate_0_bytes_list(n, m):
    # 创建一个列表，其中包含n个元素，每个元素都是m个零字节
    bytes_list = [bytes([0]) * m for _ in range(n)]
    return bytes_list

# 示例用法
n = 100  # 发送数据包数量
m = 700  # 每个数据包的大小《 MTU
time_interval = 0.001 # 发送每个数据包的时间间隔

# 时间戳写入数据包中，随数据包一起发送。
# 数据和时间通过"$"分隔，数据之间通过","或者""分隔。

# 『？？？』之前测试貌似：长度在1200左右均可以发送成功
# 但是目前实际测试长度在大于1100左右就会出现错误

bytes_list = generate_0_bytes_list(n, m-1) # HEADER_INIT占一个字节

for item in bytes_list:
    time.sleep(time_interval)
    item = bytes([HEADER_INIT]) + item
    simple.sendto(item, serverAddressPort)

formatted_end = str("end").encode()
time.sleep(time_interval)
# print("sending end packet... with lenth: ", len(bytes([HEADER_FINISH]) + formatted_end))
simple.sendto(bytes([HEADER_FINISH]) + formatted_end, serverAddressPort)

end_time = time.time()
processing_time = end_time - start_time
print(f"send total pkts with time: {processing_time} s")