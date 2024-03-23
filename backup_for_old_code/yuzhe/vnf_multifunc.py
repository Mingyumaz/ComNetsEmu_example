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

# initial parameters
TCPNUM = 6
UDPNUM = 17

svm_buffer = SVMBuffer(max_size=102400)
sync_queue_in = SVMBuffer(max_size=102400)
sync_queue_out = SVMBuffer(max_size=102400)
svm_processed = False

DEF_INIT_SETTINGS = {'is_finish': False, 'm': np.inf, 'W': None, 'proc_len': np.inf, 'proc_len_multiplier': 2, 'node_max_ext_nums': [np.inf]}
init_settings = {}
init_settings.update(DEF_INIT_SETTINGS)

TOTALNUM = 4
VNF1PROCESSNUM = [0,1]
VNF2PROCESSNUM = [2]
VNF3PROCESSNUM = [3]
current_vnf = []

_weight = [
    [4.46737612, -1.95081422, 18.29293572, -4.5986548],
    [-15.89973802, 4.45173662, -6.66900044, 11.41212648],
    [12.09920262, -27.9301321, -20.2555121, 5.15629297],
    [-0.51542267, 39.2437361, 11.1431311, -13.25246067]
]
_intercept = -0.39625843

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

pkts_payload = bytearray()
result = []

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
                svm_buffer.put(pkts_payload)

                pkts_payload = bytearray() # reset pkts_payload

                # here should use multi-threading, it will block, causing the later data cannot be received quickly if using single-threading
                simplecoin.submit_func(pid=-1, id='svm_service') # pid=-1 means use single-threading
            else:
                print('*** header else!')
                pass

@app.func(id='svm_service')
def fastica_service(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    # the function of receive is in the main function, split the recv and send, calculation time is less than send time
    global svm_buffer, svm_processed, _weight, _intercept, result, num, pro_num
    if svm_buffer.size() >= 1:
        joined_string = svm_buffer.pop()
        print(f"joined_string: {joined_string}")

    packet = simple.parse_af_packet(af_packet)
    print("run with vnf ", num)

    if packet['Protocol'] == pro_num and packet['IP_src'] != node_ip:
        if   num == 1:
            simplecoin.submit_func(pid=-1, id='vnf_1_process')
        elif num == 2:
            simplecoin.submit_func(pid=-1, id='vnf_2_process')
        elif num == 3:
            simplecoin.submit_func(pid=-1, id='vnf_3_process')
        else:
            print("not set mode with 1, 2 or 3, normal forwarding.")
            simplecoin.forward(af_packet)

        # generate the chunk and regenerate the packet
        # if res_str != '':
        #     data_bytes:bytes = str(res_str).encode()
        #     packet['Chunk']:dict = data_bytes
        #     af_packet_new:bytes = simple.recreate_af_packet_by_chunk(packet) # add udp header with chunk
        #     simplecoin.forward(af_packet_new)

# function: vnf 1, dot calculation
@app.func(id='vnf_1_process')
def f_process_vnf_1(simplecoin: SimpleCOIN.IPC):
    """
    calculate the first part of prediction model
    :param packet: the packet received from client [16 columns * n rows]
    :param model_weight: the weight vector of the svm model after fit
    :return: the result string
    """
    global sync_queue_in, svm_processed,_weight, _intercept
    if sync_queue_in.size() >= 1:
        result = ""
        joined_string = sync_queue_in.pop()
        print(f"joined_string: {joined_string}")
        # use '@' to split each line
        rows = joined_string.split("@")
        nested_list = []

        for row in rows:
            parts = row.split("#") # use '#' to split and get 4 parts
            row_list = [np.arrary(part.split(","), dtype=float) for part in parts] # convert each part to numpy array, and append to row_list
            nested_list.append(row_list) # append row_list to nested_list

        print("nested_list: ", nested_list)

        for csv_one_line in nested_list:
            # SVM process
            for i in range(TOTALNUM -1):
                if i in VNF1PROCESSNUM:
                    res_one_line = np.dot(csv_one_line[i], _weight[i].T)
                    result += str(res_one_line) + "#"
                else:
                    result += str(csv_one_line[i]) + "#"
            result += "@" # add '@' to split the rows in last column

        sync_queue_out.put(result)
        print(f"vnf 1 result: {result}")

# function: vnf 2, add intercept
@app.func(id='vnf_2_process')
def f_process_vnf_2(simplecoin: SimpleCOIN.IPC):
    """
    calculate the second part of prediction model
    :param packet: the packet received from vnf 1 [n numbers]
    :param intercept: the intercept of the svm model after fit
    :return: the result string
    """
    global sync_queue_in, svm_processed,_weight, _intercept, result
    if sync_queue_in.size() >= 1:
        joined_string = sync_queue_in.pop()
        print(f"joined_string: {joined_string}")

        if "#" in joined_string:
            # '#' is used to split the rows
            csv_list = joined_string.split("#")
            data = np.array([list(map(float, row.split(','))) for row in csv_list])
        else:
            # for one row
            data = [np.array([float(item) for item in joined_string.split(",")])]

        for result in data:
            # SVM process
            res_final = result + _intercept
            result.append(res_final)
            print(f"vnf 2 result: {result}")

# function: vnf 3, decision value judgement
def f_process_vnf_3(simplecoin: SimpleCOIN.IPC):
    """
    calculate the third part of prediction model
    :param packet: the packet received from vnf 2 [n numbers]
    :return: the final result and the accuracy
    """
    global sync_queue_in, svm_processed, _weight, _intercept, result
    if sync_queue_in.size() >= 1:
        joined_string = sync_queue_in.pop()
        print(f"joined_string: {joined_string}")

        if "#" in joined_string:
            # '#' is used to split the rows
            csv_list = joined_string.split("#")
            data = np.array([list(map(float, row.split(','))) for row in csv_list])
        else:
            # for one row
            data = [np.array([float(item) for item in joined_string.split(",")])]

        for decision_value in data:
            # SVM process
            res_final = 1 if decision_value > 0 else 0
            result.append(res_final)
            print(f"vnf 3 result: {result}")

# function: send packet directly
def send_packet(simplecoin: SimpleCOIN.IPC,):
    """
    format with pickle, take the pkts from sync_queue_out and send with udp
    """
    global sync_queue_out, svm_processed, _weight, _intercept, serverAddressPort

    if sync_queue_out.size() >= 1:
        joined_string:str = sync_queue_out.pop()
        print(f"joined_string: {joined_string}")

        formatted_chunk:bytes = str(joined_string).encode()
        chunk_arr:list = chunk_handler.get_chunks_fc(formatted_chunk)

        # recreate the packet by vnf and send to server
        for chunk in chunk_arr:
            time.sleep(0.01)
            simple.sendto(chunk, serverAddressPort)