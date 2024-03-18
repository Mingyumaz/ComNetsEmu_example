import time
import argparse
import csv
from simpleemu.simpleudp import simpleudp
from simpleemu.simpletcp import simpletcp
from simpleemu.simplecoin import SimpleCOIN
from utils.log import *
from utils.packet import *
from itertools import islice
#===============================================================================
# initial parameters
TCPNUM = 6
UDPNUM = 17

STATUS_SEND = False

MAXLINE = 10000 # 最大发送循环次数，发送行数等于MAXLINE*PROCESS_ROWS
CURRENTLINE = 0 # 当前行数
PROCESS_ROWS = 3 # 每次处理的行数
SEND_INTERVAL = 0.001 # 数据包发送间隔
VNFNUM = 3

#===============================================================================

# network setting
serverAddressPort = ("10.0.0.30", 9999)
clientAddressPort = ("10.0.0.10", 9999)

# parse args
parser = argparse.ArgumentParser(description="Using TCP or UDP")
parser.add_argument("--protocol", "-p", type=str, choices=["tcp", "udp", "t", "u"], default="udp",
                    help="choosing protocol, tcp/t or udp/u(default udp).")
args = parser.parse_args()

# tcp/udp
if args.protocol in ["udp", "u"]:
    protocol = "udp"
    simple = simpleudp
    pro_num = UDPNUM
else:
    protocol = "tcp"
    simple = simpletcp
    pro_num = TCPNUM

          
# network setting
ifce_name, node_ip = simple.get_local_ifce_ip('10.0')

app = SimpleCOIN(ifce_name=ifce_name, n_func_process=2, lightweight_mode=True)

#===============================================================================

@app.main()
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num, STATUS_SEND
    if not STATUS_SEND:
        STATUS_SEND = True
        simplecoin.submit_func(pid=1, id='send_service')

    packet = simple.parse_af_packet(af_packet)
    if packet['Protocol'] == pro_num and packet['IP_src'] != node_ip:
        chunk = packet['Chunk']
        header = int(chunk[0])
        
        # feedback from server
        if header == HEADER_FINISH:
            # print("get the feedback from server")
            print("receive", chunk[1:])
            pass
        else:
            print("header error ...")

@app.func('send_service')
def send_service(simplecoin: SimpleCOIN.IPC):
    print("send_service start ...")
    global SEND_INTERVAL, MAXLINE, PROCESS_ROWS
    for i in range(MAXLINE):
        send_str = str(i)
        payload = bytes([HEADER_INIT]) +  send_str.encode()
        time.sleep(SEND_INTERVAL)
        print("send", str(i))
        simple.sendto(payload, serverAddressPort)
    print("send_service end ...")

# 先发一个起跳包，不然可能client没有收到包就不会进入main函数，也就无法进入send_service
    
send_str = "+++++++++start+++++++++++!"
payload = bytes([HEADER_INIT]) +  str(send_str).encode()
time.sleep(SEND_INTERVAL)
simple.sendto(payload, serverAddressPort)
app.run()


# print("send_service start ...")
# for i in range(MAXLINE):
#     send_str = "hello world!"
#     payload = bytes([HEADER_INIT]) +  str(send_str).encode()
#     time.sleep(SEND_INTERVAL)
#     simple.sendto(payload, serverAddressPort)
    
    
print("send_service end ...")