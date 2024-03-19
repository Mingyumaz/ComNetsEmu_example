import numpy as np
import argparse
from simpleemu.simpleudp import simpleudp
from simpleemu.simpletcp import simpletcp
from simpleemu.simplecoin import SimpleCOIN
from utils.packet import *
from utils.log import *
import random
#===============================================================================
# initial parameters
TCPNUM = 6
UDPNUM = 17

_weight = [
    4.4673759, -1.9508139, 18.2929355, -4.59865486, -15.89973784,
    4.45173673, -6.66900071, 11.41212687, 12.09920352, -27.93013163,
    -20.25551204, 5.15629348, -0.51542374, 39.24373589, 11.14313096,
    -13.25246068
]
_intercept = -0.39625849
_weight = np.array(_weight)
_intercept = np.array([_intercept])

#===============================================================================

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
app = SimpleCOIN(ifce_name=ifce_name, n_func_process=2, lightweight_mode=True)

@app.main()
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num, num
    
    if pro_num == UDPNUM:
        # TODO: 其实应该在这里直接转发,但是要打上时间戳
        packet = simple.parse_af_packet(af_packet)
        if packet['Protocol'] == UDPNUM and packet['IP_src'] != node_ip:
            in_vnf_time = str(time.time()) # 1.接受数据时间戳
            chunk = packet['Chunk']
            header = int(chunk[0])

            if header == HEADER_INIT:
                if simplecoin.is_func_running(pid=1) == False:
                    # 空闲状态，处理数据
                    simplecoin.submit_func(pid=1, id='svm_service', args=[af_packet, in_vnf_time])
                else:
                    # 忙状态，不处理数据，直接转发  Busy state, do not process data, just forward 
                    payload = chunk[1:]
                    total_str: str = payload.decode('utf-8')
                    parts = total_str.split('$')
                    
                    # （仍旧要）打上时间戳
                    pkts_ID = parts[0] # 数据包ID
                    data_payload: str = parts[1] # 数据
                    time_list: list = parts[2].split(',') # 时间戳
                    time_list.append(str(in_vnf_time))
                    time_list.append(str(time.time()))
                    time_list.append(str(time.time()))
                    time_list.append(str(time.time()))
                    new_payload = (pkts_ID + "$" + data_payload + "$" + ','.join(map(str, time_list)) + "$" + "0").encode()
                    simplecoin.sendto(bytes([HEADER_INIT]) + new_payload, serverAddressPort)

            elif header == HEADER_FINISH:
                # 2.已经被处理完成的数据
                payload = chunk[1:]
                total_str: str = payload.decode('utf-8')
                parts = total_str.split('$')

                # （仍旧要）打上时间戳
                pkts_ID = parts[0] # 数据包ID
                data_payload: str = parts[1] # 数据
                time_list: list = parts[2].split(',') # 时间戳
                work_id = parts[3] # worker id

                time_list.append(str(in_vnf_time))    
                # NO process, only forward
                time_list.append(str(time.time()))
                time_list.append(str(time.time()))
                time_list.append(str(time.time())) # 2.准备发送数据时间戳
                new_payload = (pkts_ID + "$" + data_payload + "$" + ','.join(map(str, time_list)) + "$" + work_id).encode()
                # 发送数据
                simplecoin.sendto(bytes([header]) + new_payload, serverAddressPort)

            elif header == TEST_BEGIN or header == TEST_FINISH :
                # 3. 开始或结束标志
                payload = chunk[1:]
                time_list: list = payload.decode('utf-8').split(',') # 时间戳
                time_list.append(str(in_vnf_time))    
                # NO process, only forward
                time_list.append(str(time.time()))
                time_list.append(str(time.time()))
                time_list.append(str(time.time())) # 2.准备发送数据时间戳
                new_payload = (','.join(map(str, time_list))).encode()

                # 发送数据
                simplecoin.sendto(bytes([header]) + new_payload, serverAddressPort)
                print("Begin or end signal...")
            else:
                # 4. 错误的header
                print("____header error with ", header)

@app.func('svm_service')
def svm_service(simplecoin: SimpleCOIN.IPC, af_packet: bytes, in_vnf_time: str):
    global num

    # print("svm_service start...")

    packet = simple.parse_af_packet(af_packet)
    in_procss_time = time.time() # 计算开始处理时间
    chunk = packet['Chunk']
    # header = int(chunk[0])
    payload = chunk[1:]
    total_str: str = payload.decode('utf-8')
    parts = total_str.split('$')

    # 将收到数据切分为数据和时间戳
    pkts_ID = parts[0] # 数据包ID
    data_payload: str = parts[1] # 数据
    time_list: list = parts[2].split(',') # 时间戳
    
    csv_list = data_payload.split("#")
    data = np.array([list(map(float, row.split(','))) for row in csv_list])
    result = []
    for csv_one_line in data:
        decision_value = np.dot(csv_one_line, _weight.T) + _intercept
        if decision_value > 0:
            res_final = 1
        else:
            res_final = 0
        result.append(res_final)

    resultstr = ','.join(map(str, result))
    out_procss_time = time.time() # 计算结束处理时间

    time_list.append(in_vnf_time)
    time_list.append(str(in_procss_time))
    time_list.append(str(out_procss_time))
    time_list.append(str(time.time())) # out_vnf_time

    new_payload = (pkts_ID + "$" + resultstr + "$" + ','.join(map(str, time_list)) + "$" + str(num)).encode()
    simplecoin.sendto(bytes([HEADER_FINISH]) + new_payload, serverAddressPort)

if __name__ == "__main__":
    app.run()