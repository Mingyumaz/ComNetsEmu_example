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


# def load_svm_model(path):
#     global already_load_svm_model
#     if not already_load_svm_model:
#         # load the fitted model SVM
#         svm = load(path)

#         _weight = svm.coef_ # the weight vector of the svm model after fit
#         _intercept = svm.intercept_ # the intercept of the svm model after fit

#         print('weight:',_weight)
#         print('intercept:',_intercept)
#         already_load_svm_model = True

#         return _weight, _intercept
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
app = SimpleCOIN(ifce_name=ifce_name, n_func_process=1, lightweight_mode=True)

@app.main()
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num, num

    if pro_num == UDPNUM:
        packet = simple.parse_af_packet(af_packet)
        if packet['Protocol'] == UDPNUM and packet['IP_src'] != node_ip:
            in_time = time.time() # 1.接受数据时间戳
            chunk = packet['Chunk']
            header = int(chunk[0])
            payload = chunk[1:]

            if header == HEADER_INIT:
                # 1.未被处理的数据
                total_str: str = payload.decode('utf-8')
                parts = total_str.split('$', 1)

                # 将收到数据切分为数据和时间戳
                data_payload: str = parts[0] # 数据
                time_list: list = parts[1].split(',') # 时间戳
                time_list[2*num-1] = str(in_time)

                random_number = random.randint(1, 10) # 随机数进行随机处理
                if (num == 1 or num == 2) and random_number > 4:
                # if num == 1:
                    # 1.1 并不处理数据而是forword
                    time_list[2*num] = str(time.time()) # 准备发送数据时间戳
                    new_payload = (data_payload + "$" + ','.join(map(str, time_list))).encode()

                    # 发送数据
                    simplecoin.sendto(bytes([HEADER_INIT]) + new_payload, serverAddressPort)
                    # simplecoin.forward(af_packet)
                    # print("No process")
                else:
                    # 1.2 处理，最后一个节点一定处理未完成的数据包
                    csv_list = data_payload.split("#")
                    data = np.array([list(map(float, row.split(','))) for row in csv_list])
                    # print("processing data...")
                    result = []
                    for csv_one_line in data:
                        decision_value = np.dot(csv_one_line, _weight.T) + _intercept
                        if decision_value > 0:
                            res_final = 1
                        else:
                            res_final = 0
                        result.append(res_final)

                    resultstr = ','.join(map(str, result))

                    time_list[2*num] = str(time.time()) # 2.准备发送数据时间戳
                    new_payload = (resultstr + "$" + ','.join(map(str, time_list))).encode()

                    # 发送数据
                    simplecoin.sendto(bytes([HEADER_FEEDBACK]) + new_payload, clientAddressPort)

            # elif header == HEADER_FINISH:
            #     # 2.已经被处理完成的数据
            #     # total_str: str = payload.decode('utf-8')
            #     # parts = total_str.split('$', 1)

            #     # # 将收到数据切分为数据和时间戳
            #     # data_payload: str = parts[0] # 数据
            #     # time_list: list = parts[1].split(',') # 时间戳
            #     # time_list[2*num-1] = str(in_time)

            #     # # NO process, only forward

            #     # time_list[2*num] = str(time.time()) # 2.准备发送数据时间戳
            #     # new_payload = (data_payload + "$" + ','.join(map(str, time_list))).encode()
            #     # 发送数据
            #     # simplecoin.sendto(bytes([header]) + new_payload, serverAddressPort)
            #     simplecoin.sendto(bytes([HEADER_FEEDBACK]) + payload, clientAddressPort)

            elif header == TEST_BEGIN or header == TEST_FINISH :
                # 3. 开始或结束标志
                time_list: list = payload.decode('utf-8').split(',') # 时间戳
                time_list[2*num-1] = str(in_time)
                # NO process, only forward

                time_list[2*num] = str(time.time()) # 2.准备发送数据时间戳
                new_payload = (','.join(map(str, time_list))).encode()

                # 发送数据
                simplecoin.sendto(bytes([header]) + new_payload, serverAddressPort)
                print("Begin or end signal...")
            elif header == HEADER_FEEDBACK:
                # 4. just forward
                # simplecoin.sendto(bytes([HEADER_FEEDBACK]) + payload, clientAddressPort)
                simplecoin.forward(af_packet)
            else:
                # 5. 错误的header
                print("____header error with ", header)

if __name__ == "__main__":
    app.run()