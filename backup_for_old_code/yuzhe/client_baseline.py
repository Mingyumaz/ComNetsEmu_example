import time
import argparse
import csv
from simpleemu.simpleudp import simpleudp
from utils.log import *
from utils.packet import *
from itertools import islice
#===============================================================================
MAXLINE = 10000 # 最大发送循环次数，发送行数等于MAXLINE*PROCESS_ROWS
PKTS_ID = 0 # 当前行数
PROCESS_ROWS = 3 # 每次处理的行数
SEND_INTERVAL = 0.003 # 数据包发送间隔
VNFNUM = 3
#===============================================================================
def read_and_format_csv(filename, chunk_size=1):
    with open(filename, 'r') as file:
        csv_reader = csv.reader(file)
        while True:
            chunk = [','.join(row[-16:]) for row in islice(csv_reader, chunk_size)]
            if not chunk:
                break
            yield '#'.join(chunk)

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

#===============================================================================


# TIME, just append the time to the end of the data
time_list = [0]

# 1.发送开始信号
# data format [Header(begin)] + {[Time]}
start_time = time.time()
time_list[0] = str(start_time)
begin_payload = bytes([TEST_BEGIN]) + (','.join(map(str, time_list))).encode()
simple.sendto(begin_payload, serverAddressPort)

# 2.发送数据
# data format: [Header] + { [pkts ID] + $ + [Data with #] + $ + [Time] + $ + [Active VNF(worker)] }
for data_rows in read_and_format_csv('test_data_feature.csv', PROCESS_ROWS):
    if PKTS_ID == MAXLINE:
        break
    PKTS_ID += 1

    payload: str = str(PKTS_ID) + "$" + str(data_rows)

    time_list[0] = str(time.time())
    payload_timestamp = "$" + ','.join(map(str, time_list))
    send_data = bytes([HEADER_INIT]) + (payload + payload_timestamp + "$" + "0").encode()

    # print(f"Send data: {send_data}")

    time.sleep(SEND_INTERVAL)
    simple.sendto(send_data, serverAddressPort) # 发送数据和时间

# 3.发送结束信号
# data format [Header(end)] + {[Time]}
time.sleep(SEND_INTERVAL)
end_time = time.time()
time_list[0] = str(end_time)
end_payload = bytes([TEST_FINISH]) + (','.join(map(str, time_list))).encode()
simple.sendto(end_payload, serverAddressPort)

# 4.打印发送数量等信息
print(f"Send {PKTS_ID*PROCESS_ROWS + 2} lines data, with 1 begin and 1 end message.")