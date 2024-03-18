import time
import argparse
import csv
from simpleemu.simpleudp import simpleudp
from simpleemu.simplecoin import SimpleCOIN
from utils.log import *
from utils.packet import *
from itertools import islice
#===============================================================================
MAXLINE = 10000 # 最大发送循环次数，发送行数等于MAXLINE*PROCESS_ROWS
CURRENTLINE = 0 # 当前行数
PROCESS_ROWS = 3 # 每次处理的行数
SEND_INTERVAL = 0.001 # 数据包发送间隔
VNFNUM = 3
#===============================================================================
def read_and_format_csv(filename, chunk_size=10):
    with open(filename, 'r') as file:
        csv_reader = csv.reader(file)
        while True:
            chunk = []
            for row in islice(csv_reader, chunk_size):
                # PS, 这里不太一样，只取每行的最后16列，并每4列作为一组，用#连接
                formatted_row = '#'.join([','.join(row[-16:][i:i+4]) for i in range(0, 16, 4)])
                chunk.append(formatted_row)
            if not chunk:
                break
            yield '@'.join(chunk)

# parse args
parser = argparse.ArgumentParser(description="using TCP or UDP")
parser.add_argument("--protocol", "-p", type=str, choices=["tcp", "udp", "t", "u"], default="udp",
                    help="choosing protocol, tcp/t or udp/u(default udp).")
args = parser.parse_args()

# TCP/UDP
if args.protocol in ["udp", "u"]:
    protocol = "udp"
    simple = simpleudp

# network setting
ifce_name, node_ip = simple.get_local_ifce_ip('10.0')

# log_file(ifce_name).debug(f"ifce_name = {ifce_name}, node_ip = {node_ip}")

app = SimpleCOIN(ifce_name=ifce_name, n_func_process=5, lightweight_mode=True)
serverAddressPort = ("10.0.0.30", 9999)
clientAddressPort = ("10.0.0.10", 9999)

#===============================================================================

# TIME
# 加入测试时间戳，用于测试数据包发送时间，时间随数据包一起发送。
# 数据和时间通过"$"分隔，数据之间通过","或者""分隔。
time_list = [0 for _ in range(2*VNFNUM+3)]

# 1.发送开始信号
start_time = time.time()
time_list[0] = str(start_time)
begin_payload = bytes([TEST_BEGIN]) + (','.join(map(str, time_list))).encode()
simple.sendto(begin_payload, serverAddressPort)

# 2.发送数据
for formatted_chunk in read_and_format_csv('test_data_feature.csv', PROCESS_ROWS):

    if CURRENTLINE == MAXLINE:
        break
    CURRENTLINE += 1
    payload = bytes([HEADER_INIT]) +  str(formatted_chunk).encode() # 未处理 HEADER_INIT
    time_list[0] = str(time.time())
    payload_timestamp = ("$" + ','.join(map(str, time_list))).encode()

    time.sleep(SEND_INTERVAL)
    # simple.sendto(payload, serverAddressPort) # 仅发送数据，不发送时间
    # print(payload + payload_timestamp)
    simple.sendto(payload + payload_timestamp, serverAddressPort) # 发送数据和时间

# 3.发送结束信号
time.sleep(SEND_INTERVAL)
end_time = time.time()
time_list[0] = str(end_time)
end_payload = bytes([TEST_FINISH]) + (','.join(map(str, time_list))).encode()
simple.sendto(end_payload, serverAddressPort)

# 4.打印发送数量等信息
print(f"Send {CURRENTLINE*PROCESS_ROWS + 2} lines data, with 1 begin and 1 end message.")