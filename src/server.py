"""
This server only receives the data from the client and print it out
The VNF will have process the data function
"""

import argparse
from simpleemu.simpleudp import simpleudp
from simpleemu.simpletcp import simpletcp
from simpleemu.simplecoin import SimpleCOIN
from svmbuffer import SVMBuffer
from utils.packet import *
from utils.log import *
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

def contains_non_zero_one(numbers):
    for num in numbers:
        if num != 0 and num != 1:
            return True
    return False

_weight = [
    4.46737612, -1.95081422, 18.29293572, -4.5986548, -15.89973802,
    4.45173662, -6.66900044, 11.41212648, 12.09920262, -27.9301321,
    -20.2555121, 5.15629297, -0.51542267, 39.2437361, 11.1431311,
    -13.25246067
]
_intercept = -0.39625843

# network
serverAddressPort = ("10.0.0.30", 9999)
clientAddressPort = ("10.0.0.10", 9999)

# parse args
parser = argparse.ArgumentParser(description="Using TCP or UDP")
parser.add_argument("--protocol", "-p", type=str, choices=["tcp", "udp", "t", "u"], default="udp",
                    help="choosing protocol, tcp/t or udp/u(default udp)")
args = parser.parse_args() # to parse command line arguments to determine which protocol to use

# tcp/udp, tcp is not supported yet
if args.protocol in ["udp", "u"]:
    protocol = "udp"
    simple = simpleudp
    pro_num = 17
else:
    protocol = "tcp"
    simple = simpletcp
    simple.listen(serverAddressPort)
    pro_num = 6

# network setting
ifce_name, node_ip = simple.get_local_ifce_ip('10.0.')

# simple coin, setup network interface and process
app = SimpleCOIN(ifce_name=ifce_name, n_func_process=2, lightweight_mode=True)

pkts_payload = bytearray()
result = []

# main function
@app.main()
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num, first, pkts_payload, svm_buffer

    if pro_num == TCPNUM: # TCP is not supported yet
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
                simplecoin.submit_func(pid=-1, id='printout') # pid=-1 means use single-threading
            else:
                print('*** header else!')
                pass

@app.func(id='printout')
def fastica_service(simplecoin: SimpleCOIN.IPC):
    global svm_buffer, svm_processed, _weight, _intercept, result
    if svm_buffer.size() >= 1:
        joined_string = svm_buffer.pop()
        print(f"joined_string: {joined_string}")

@app.func(id='svm_service')
def fastica_service(simplecoin: SimpleCOIN.IPC):
    global svm_buffer, svm_processed, _weight, _intercept, result
    if svm_buffer.size() >= 1:
        joined_string = svm_buffer.pop()
        print(f"joined_string: {joined_string}")

        if "#" in joined_string: # split the string by '#' and convert to float
            split_list = joined_string.split('#') # split the string by '#'
            split_list = [float(i) for i in split_list] # convert to float
        else:
            split_list = [float(joined_string)]

        if contains_non_zero_one(split_list):
            return

        # calculate the accuracy
        zero_count = split_list.count(0)
        total_count = len(split_list)
        ratio = zero_count / total_count * 100 if total_count > 0 else 0
        print(f"The current SCORE: {ratio} %")

if __name__ == "__main__":
    app.run()