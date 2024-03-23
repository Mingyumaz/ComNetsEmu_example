import argparse
from simpleemu.simpleudp import simpleudp
from simpleemu.simpletcp import simpletcp
from simpleemu.simplecoin import SimpleCOIN
from utils.packet import *
from utils.log import *

# network
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
    pro_num = 17
else:
    protocol = "tcp"
    simple = simpletcp
    pro_num = 6

num = args.num # set the function number of the vnf

# network setting
ifce_name, node_ip = simple.get_local_ifce_ip('10.0')

# Simple coin
app = SimpleCOIN(ifce_name=ifce_name, n_func_process=1, lightweight_mode=True)

@app.main()
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num, num
    packet = simple.parse_af_packet(af_packet)
    if packet['Protocol'] == pro_num and packet['IP_src'] != node_ip:
        in_time = time.time() # 1.接受数据时间戳
        chunk = packet['Chunk']
        header = int(chunk[0])
        payload = chunk[1:]

        if header == HEADER_INIT:
            # 含有数据
            if payload:
                total_str: str = payload.decode('utf-8')
                parts = total_str.split('$', 1)
            
                # 将收到数据切分为数据和时间戳
                data_payload: str = parts[0] # 数据
                time_list: list = parts[1].split(',') # 时间戳
                time_list[2*num-1] = str(in_time)
                # NO process, only forward

                time_list[2*num] = str(time.time()) # 2.准备发送数据时间戳
                new_payload = (data_payload + "$" + ','.join(map(str, time_list))).encode()
                # 发送数据
                simplecoin.sendto(bytes([HEADER_INIT]) + new_payload, serverAddressPort)

        elif header == TEST_BEGIN or header == TEST_FINISH:
            # 不含有数据
            if payload:
                # 开始和结束信号仅有时间戳，没有data，不需要切割处理
                time_list: list = payload.decode('utf-8').split(',') # 时间戳
                time_list[2*num-1] = str(in_time)
                # NO process, only forward

                time_list[2*num] = str(time.time()) # 2.准备发送数据时间戳
                new_payload = (','.join(map(str, time_list))).encode()

                # 发送数据
                simplecoin.sendto(bytes([header]) + new_payload, serverAddressPort)
            print("Begin or end signal...")

        elif header == HEADER_FEEDBACK:
            # just forward
            simplecoin.forward(af_packet)
        else:
            print("____header error with ", header)


app.run()