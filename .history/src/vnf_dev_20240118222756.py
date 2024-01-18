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

TCPNUM = 6
UDPNUM = 17

svm_buffer = SVMBuffer(max_size=102400)
svm_processed = False

DEF_INIT_SETTINGS = {'is_finish': False, 'm': np.inf, 'W': None, 'proc_len': np.inf, 'proc_len_multiplier': 2, 'node_max_ext_nums': [np.inf]}
init_settings = {}
init_settings.update(DEF_INIT_SETTINGS)

def decode_packet_vnf_1(joined_string):
    """
    decode the packet from string to numpy array [2 dimension, 16 columns * n rows]

    :param packet: the packet received from the server
    :return: the numpy array
    """
    if "#" in joined_string:
        csv_list = joined_string.split("#") # split the string by '#'
        print(csv_list)

        # if csv_list and len(csv_list[0]) != 16:
        #     return ''

        data = np.array([list(map(float, row.split(','))) for row in csv_list])
    else:
        data = [np.array([float(item) for item in joined_string.split(",")])]

    print("======================================")
    print(data)
    print("======================================")
    return data

def encode_packet_vnf_1(data):
    """
    encode the packet from numpy array to string.
    `data` is a list of float numbers.
    """
    res_string = '#'.join([str(item) for item in data])
    return res_string


def decode_packet_vnf_2(joined_string):
    """
    decode the packet from string to numpy array [1 dimension]

    """
    print(joined_string)

    if "#" in joined_string:
        data = [float(item) for item in joined_string.split("#")]
    else:
        data = [float(joined_string)]

    print("======================================")
    print(data)
    print("======================================")

    return data

def vnf_1_process(packet, model_weight):
    """
    calculate the first part of prediction model
    :param packet: the packet received from client [16 columns * n rows]
    :param model_weight: the weight vector of the svm model after fit
    :return: the result string
    """

    print("vnf 1 process")
    # print(packet['Chunk'])
    print("---------begin---------")
    res = []

    # get the csv data from packet
    joined_string = str(packet['Chunk'].decode())
    data = decode_packet_vnf_1(joined_string)

    if data[0].shape[0] != 16: # if the csv data is not 16 columns
        return ''

    for csv_one_line in data:

        # calculate the first part of prediction model for dot calculation
        res_one_line = np.dot(csv_one_line, model_weight.T)
        res.append(res_one_line)

    res_str = encode_packet_vnf_1(res)
    print("vnf 1 result", res_str)
    return res_str


def vnf_2_process(packet, intercept):
    """
    calculate the second part of prediction model
    :param packet: the packet received from vnf 1 [n numbers]
    :param intercept: the intercept of the svm model after fit
    :return: the result string
    """
    res = []

    joined_string = str(packet['Chunk'].decode())

    if (joined_string == '0#0#0#0#0') or (joined_string == '0'):
        return ''

    data = decode_packet_vnf_2(joined_string)
    for res_temp in data:

        # just calculate one part, add with intercept
        res_temp += intercept
        res.append(res_temp)

    print("vnf2 result", res)
    res_str = encode_packet_vnf_1(res) # same to vnf 1 encode
    return res_str


def vnf_3_process(packet):
    """
    calculate the third part of prediction model
    :param packet: the packet received from vnf 2 [n numbers]
    :return: the final result and the accuracy
    """

    res = []

    # get the csv data from packet
    joined_string = str(packet['Chunk'].decode())
    data = decode_packet_vnf_2(joined_string)
    for res_temp in data:
        # judege the value > ? <= 0
        res_final = 1 if res_temp > 0 else 0
        res.append(res_final)

    print("vnf3 result", res)
    res_str = encode_packet_vnf_1(res)
    print("vnf3 result string", res_str)
    return res_str


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
result = []

# already_load_svm_model = False
# _weight, _intercept = load_svm_model('./svm_model.joblib')

_weight = [
    4.46737612, -1.95081422, 18.29293572, -4.5986548, -15.89973802,
    4.45173662, -6.66900044, 11.41212648, 12.09920262, -27.9301321,
    -20.2555121, 5.15629297, -0.51542267, 39.2437361, 11.1431311,
    -13.25246067
]
_intercept = -0.39625843

@app.main()
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num, first, pkts_payload, svm_buffer

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
            res_str = vnf_1_process(packet, _weight)
        elif num == 2:
            res_str = vnf_2_process(packet, _intercept)
        elif num == 3:
            res_str = vnf_3_process(packet)
        else:
            print("not set mode with 1, 2 or 3, normal forwarding.")
            exit()

        # generate the chunk and regenerate the packet
        if res_str != '':
            data_bytes:bytes = str(res_str).encode()
            packet['Chunk']:dict = data_bytes
            af_packet_new:bytes = simple.recreate_af_packet_by_chunk(packet) # add udp header with chunk
            simplecoin.forward(af_packet_new)

app.run()