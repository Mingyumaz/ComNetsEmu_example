# 发送随机数据包到服务器，测试链路是否正确，以及能否处理数据包

import numpy as np
import argparse
from simpleemu.simpleudp import simpleudp
from simpleemu.simpletcp import simpletcp
from simpleemu.simplecoin import SimpleCOIN
from utils.packet import *
from utils.log import *
from joblib import load
import random

# initial parameters
TCPNUM = 6
UDPNUM = 17

# network setting
serverAddressPort = ("10.0.0.30", 9999)
clientAddressPort = ("10.0.0.10", 9999)

# parse args
parser = argparse.ArgumentParser(description="Using TCP or UDP")
parser.add_argument("--protocol", "-p", type=str, choices=["tcp", "udp", "t", "u"], default="udp",
                    help="choosing protocol, tcp/t or udp/u(default udp)")
parser.add_argument("--num", "-n", type=int, choices=[1, 2, 3], default=1,
                    help="which number is this switch. 1, 2 or 3 (default 1)")
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

num = args.num # set the function number of the vnf

ifce_name, node_ip = simple.get_local_ifce_ip('10.0')

# simple coin
app = SimpleCOIN(ifce_name=ifce_name, n_func_process=1, lightweight_mode=True)

@app.main()
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num, num

    if pro_num == UDPNUM:
        packet = simple.parse_af_packet(af_packet)
        if packet['Protocol'] == UDPNUM and packet['IP_src'] != node_ip:

            # 测试发现，处理时间大约在 processing time: 1.6927719116210938e-05 
            start_time = time.time()
            
            chunk = packet['Chunk']
            header = int(chunk[0])
            print("header:", header)
            payload = chunk[1:]

            if header == HEADER_INIT:
                # 未被处理
                random_number = random.randint(1, 10)
                if (num == 1 or num == 2) and random_number > 4:
                    simplecoin.forward(af_packet) # 摆烂
                    print("======================")
                else:
                # 最后一个节点一定处理未完成的数据包
                # simplecoin.submit_func(pid=-1, id='svm_service', args=(payload, packet, ))
                    if payload:
                        payload: str = payload.decode('utf-8')

                        m = 699
                        new_payload:bytes = bytes([1]) * m

                        print("new_payload:", new_payload)

                        packet['Chunk'] = bytes([HEADER_FINISH]) + new_payload
                        af_packet_new = simple.recreate_af_packet_by_chunk(packet)
                        # simplecoin.forward(af_packet_new)
                        simplecoin.sendto(af_packet_new, serverAddressPort)
                        print("calculate finish!")

            elif header == HEADER_FINISH:
                # 已经被处理
                simplecoin.forward(af_packet)
                print("finish!")
            else:
                print("header error")

            end_time = time.time()
            print(f"processing time: {end_time - start_time} s")

if __name__ == "__main__":
    app.run()