import numpy as np
import argparse
from simpleemu.simpleudp import simpleudp
from simpleemu.simpletcp import simpletcp
from simpleemu.simplecoin import SimpleCOIN
from utils.packet import *
from utils.log import *
from joblib import load
from svmbuffer import SVMBuffer
import pickle
import io
import time

##################################################
# Init paratmeters
TCPNUM = 6
UDPNUM = 17

sync_queue_in = SVMBuffer(max_size=102400)
sync_queue_out = SVMBuffer(max_size=102400)
svm_processed = False

DEF_INIT_SETTINGS = {'is_finish': False, 'm': np.inf, 'W': None, 'proc_len': np.inf, 'proc_len_multiplier': 2, 'node_max_ext_nums': [np.inf]}
init_settings = {}
init_settings.update(DEF_INIT_SETTINGS)

serverAddressPort = ("10.0.0.30", 9999) # Server address

TOTALNUM = 4 # 总共有4列（16列分为4组）数据
# VNF1PROCESSNUM = [0,1,2,3],目前是16列分为4组，
# 这里给VNF1处理0,1列，VNF2处理2列，VNF3处理3列
VNF1PROCESSNUM = [0,1]
VNF2PROCESSNUM = [2]
VNF3PROCESSNUM = [3]
current_vnf = [] # 标记当前是哪个VNF在处理数据

_weight = [
    [4.46737612, -1.95081422, 18.29293572, -4.5986548],
    [-15.89973802, 4.45173662, -6.66900044, 11.41212648], 
    [12.09920262, -27.9301321, -20.2555121, 5.15629297], 
    [-0.51542267, 39.2437361, 11.1431311, -13.25246067]
]
_intercept = -0.39625843

# already_load_svm_model = False
# _weight, _intercept = load_svm_model('./svm_model.joblib')
##################################################

def load_svm_model(path):
    global already_load_svm_model
    if not already_load_svm_model:
        # load the fitted model SVM
        svm = load(path)

        _weight = svm.coef_ # the weight vector of the svm model after fit
        _intercept = svm.intercept_ # the intercept of the svm model after fit

        print('weight:',_weight)
        print('intercept:',_intercept)
        already_load_svm_model = True

        return _weight, _intercept

# network setting
serverAddressPort = ("10.0.0.30", 9999)
clientAddressPort = ("10.0.0.10", 9999)

# parse args
parser = argparse.ArgumentParser(description="Using TCP or UDP")
parser.add_argument("--protocol", "-p", type=str, choices=["tcp", "udp", "t", "u"], default="udp",
                    help="choosing protocol, tcp/t or udp/u(default udp)")
parser.add_argument("--num", "-n", type=int, choices=[1, 2, 3], default=1,
                    help="which number is this switch. 1, 2 or 3(default 1)")
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

pkts_payload = bytearray()

@app.main()
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num, first, pkts_payload, sync_queue_in

    if pro_num == TCPNUM:
        print('*** TCP is not supported yet!')
        conn, addr = simple.accept(serverAddressPort)
        first = False

    if pro_num == UDPNUM:
        packet = simple.parse_af_packet(af_packet)
        if packet['Protocol'] == UDPNUM and packet['IP_src'] != node_ip:
            chunk = packet['Chunk']
            header = int(chunk[0])
            if header == HEADER_CLEAR_CACHE:
                print('*** clearing cache!')

            elif header == HEADER_INIT:
                print('*** initializing!')
                pkts_payload += chunk[1:]

            elif header == HEADER_DATA:
                print('*** header data!')
                pkts_payload += chunk[1:]

            elif header == HEADER_FINISH:
                print('*** header finish!')
                pkts_payload += chunk[1:]
                pkts_payload = pickle.load(io.BytesIO(pkts_payload)).decode('utf-8')
                sync_queue_in.put(pkts_payload)

                pkts_payload = bytearray() # reset pkts_payload

                # here should use multi-threading, it will block, causing the later data cannot be received quickly if using single-threading
                simplecoin.submit_func(pid=-1, id='svm_service', args=(af_packet,)) # pid=-1 means use single-threading
            else:
                print('*** header else!')
                pass

@app.func(id='svm_service')
def svm_service(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    # the function of receive is in the main function, split the recv and send, calculation time is less than send time
    global num, pro_num, current_vnf

    packet = simple.parse_af_packet(af_packet)

    if packet['Protocol'] == pro_num and packet['IP_src'] != node_ip:
        print("run with vnf ", num)
        if   num == 1:
            current_vnf = VNF1PROCESSNUM
        elif num == 2:
            current_vnf = VNF2PROCESSNUM
        elif num == 3:
            current_vnf = VNF3PROCESSNUM

        if sync_queue_in.size() >= 1:
            result = ""
            joined_string:str = sync_queue_in.pop()
            
            print(f"joined_string: {joined_string}")

            rows = joined_string.split('@')# 按@分割得到每一行
            nested_list = []

            for row in rows:
                parts = row.split('#') # 按#分割得到四个部分
                row_list = [np.array(part.split(','), dtype=float) for part in parts] # 将每个部分转换为NumPy数组，并加入到行列表中
                nested_list.append(row_list) # 将行列表加入到最终列表中
            
            print(f"nested_list: {nested_list}")


            # (为下面这个循环处理解释) 这里收到的数据将会是这样：
            #
            # 计划让VNFx可以处理任意列的数据，而不是固定的，可以随意选择。因为数据按列分组，然后计算。
            #
            # VNF1 中 (假设收到数据有3行，当然几行都可能)，他们会是这样(其实数据只是一行，
            # 这里分行看会清楚一些)：
            #--- 1, 2, 3, 4 # 5, 6, 7, 8 # 9, 10, 11, 12 # 13, 14, 15, 16 @ 
            #--- 1, 2, 3, 4 # 5, 6, 7, 8 # 9, 10, 11, 12 # 13, 14, 15, 16 @
            #--- 1, 2, 3, 4 # 5, 6, 7, 8 # 9, 10, 11, 12 # 13, 14, 15, 16 @ ......
            #--- 那么，在设定的 VNF1PROCESSNUM (目前我设定[0, 1], 代表第一个竖列分区和第二个竖列分区) 中
            # ，我们只需要处理第一列和第二列，即：
            #--- 1, 2, 3, 4 # 5, 6, 7, 8 @
            #--- 1, 2, 3, 4 # 5, 6, 7, 8 @
            #--- 1, 2, 3, 4 # 5, 6, 7, 8 @
            # 这四行数据，然后进行运算，得到结果，再将结果和第三列和第四列拼接起来，即：
            #--- value # value # 9, 10, 11, 12 # 13, 14, 15, 16 @
            #--- value # value # 9, 10, 11, 12 # 13, 14, 15, 16 @
            #--- value # value # 9, 10, 11, 12 # 13, 14, 15, 16 @ ......
            # 最后，发送出去给VNF2.
            #
            # 那么如果我设定VNF1PROCESSNUM处理第一列和第三列，那么就是：VNF1PROCESSNUM=[0, 2]
            # 那么就是：
            #--- value # 5, 6, 7, 8 # value # 13, 14, 15, 16 @
            #--- value # 5, 6, 7, 8 # value # 13, 14, 15, 16 @
            #--- value # 5, 6, 7, 8 # value # 13, 14, 15, 16 @ ......
            # 然后发送给VNF2, 以此类推。

            for csv_one_line in nested_list:
                # svm process
                for i in range(TOTALNUM):
                    if i in current_vnf:
                        res_one_line = np.dot(csv_one_line[i], _weight[i])
                        result += str(res_one_line) + "#"
                    else:
                        result += ','.join(map(str, csv_one_line[i])) + "#"
                result = result[:-1] + "@" # add @ to split the rows in last columns
            
            sync_queue_out.put(result)
            print(f"result: {result}")

            simplecoin.submit_func(pid=-1, id='send_packet')

        # 这里先别删
        # # generate the chunk and regenerate the packet
        # if res_str != '':
        #     data_bytes:bytes = str(res_str).encode()
        #     packet['Chunk']:dict = data_bytes
        #     af_packet_new:bytes = simple.recreate_af_packet_by_chunk(packet) # add udp header with chunk
        #     simplecoin.forward(af_packet_new)


@app.func(id='send_packet')
def send_packet(simplecoin: SimpleCOIN.IPC,):
    """
    Format with pickle, take the pkts from sync_queue_out and send with udp
    """
    global sync_queue_out, svm_processed, _weight, _intercept, serverAddressPort

    if sync_queue_out.size() >= 1:
        joined_string:str = sync_queue_out.pop()
        print(f"joined_string: {joined_string}")

        formatted_chunk:bytes = str(joined_string).encode()
        chunk_arr:list = chunk_handler.get_chunks_fc(formatted_chunk)

        # recreate the packet by vnf and send to server
        for chunk in chunk_arr:
            time.sleep(0.1)
            simple.sendto(chunk, serverAddressPort)

if __name__ == "__main__":
    app.run()