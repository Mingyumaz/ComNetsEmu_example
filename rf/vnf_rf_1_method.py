import numpy as np
import argparse
from simpleemu.simpleudp import simpleudp
from simpleemu.simpletcp import simpletcp
from simpleemu.simplecoin import SimpleCOIN
from utils.packet import *
from utils.log import *
import joblib
import numpy as np

#===============================================================================
# init paratmeters
TCPNUM = 6
UDPNUM = 17

#===============================================================================
# network setting
serverAddressPort = ("10.0.0.30", 9999)
clientAddressPort = ("10.0.0.10", 9999)

# parse args
parser = argparse.ArgumentParser(description="Using TCP or UDP")
parser.add_argument("--protocol", "-p", type=str, choices=["tcp", "udp", "t", "u"], default="udp",
                    help="choosing protocol, tcp/t or udp/u (default udp)")
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

if num == 3:
    AFTER_PROCESS = HEADER_FINISH
else:
    AFTER_PROCESS = HEADER_INIT

# Load the model
model_file_name = "rf_model_subset_" + str(num-1) + ".joblib"
with open(model_file_name, 'rb') as file:
    random_forest_model = joblib.load(file)

ifce_name, node_ip = simple.get_local_ifce_ip('10.0')
# simple coin
app = SimpleCOIN(ifce_name=ifce_name, n_func_process=1, lightweight_mode=True)

@app.main()
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num, num, random_forest_model, AFTER_PROCESS

    if pro_num == UDPNUM:
        packet = simple.parse_af_packet(af_packet)
        if packet['Protocol'] == UDPNUM and packet['IP_src'] != node_ip:
            in_vnf_time = str(time.time()) # 1.接受数据时间戳
            chunk = packet['Chunk']
            header = int(chunk[0])
            payload = chunk[1:]

            if header == HEADER_INIT:
                # 1. 需要计算
                total_str: str = payload.decode('utf-8')
                parts = total_str.split('$')

                # （仍旧要）打上时间戳
                pkts_ID = parts[0] # 数据包ID
                data_payload: str = parts[1] # 数据
                time_list: list = parts[2].split(',') # 时间戳
                work_id = parts[3] # worker id

                time_begin_process = time.time()
                
                if "@" in data_payload: 
                    rows = data_payload.split('@')
                    before_res = rows[1] + "&" # 前面VNF的预测结果
                    data_payload = rows[0] # 数据
                else:
                    before_res = ""
                
                csv_list = data_payload.split("#")
                data = np.array([list(map(float, row.split(','))) for row in csv_list])
                result = random_forest_model.predict(data)
                
                result_str = before_res + ','.join(map(str, result)) 

                time_end_process = time.time()

                time_list.append(str(in_vnf_time))    
                # NO process, only forward
                time_list.append(str(time_begin_process))
                time_list.append(str(time_end_process))
                time_list.append(str(time.time()))
                AFTER_PROCESS
                if num != 3:
                    # need to send source data, because the next tree need to judege.
                    new_payload = (pkts_ID + "$" + data_payload + "@" + result_str + "$" + ','.join(map(str, time_list)) + "$" + work_id).encode()
                else:
                    # only send the result from 3 tree, no need to send the source data
                    new_payload = (pkts_ID + "$" + result_str + "$" + ','.join(map(str, time_list)) + "$" + "3").encode()

                simplecoin.sendto(bytes([AFTER_PROCESS]) + new_payload, serverAddressPort)

            elif header == TEST_BEGIN or header == TEST_FINISH :
                # 2. 开始或结束标志
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
                # 3.错误的header
                print("____header error with ", header)

if __name__ == "__main__":
    app.run()