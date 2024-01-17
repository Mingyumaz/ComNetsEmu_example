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

DEF_INIT_SETTINGS = {'is_finish': False, 'm': np.inf, 'W': None, 'proc_len': np.inf,
                     'proc_len_multiplier': 2, 'node_max_ext_nums': [np.inf]}
init_settings = {}
init_settings.update(DEF_INIT_SETTINGS)

def contains_non_zero_one(numbers):
    for num in numbers:
        if num != 0 and num != 1:
            return True
    return False

# already_load_svm_model = False
# _weight, _intercept = load_svm_model('./svm_model.joblib')
_weight = [
    4.46737612, -1.95081422, 18.29293572, -4.5986548, -15.89973802,
    4.45173662, -6.66900044, 11.41212648, 12.09920262, -27.9301321,
    -20.2555121, 5.15629297, -0.51542267, 39.2437361, 11.1431311,
    -13.25246067
]
_intercept = -0.39625843


# Network
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
    pro_num = UDPNUM
else:
    protocol = "tcp"
    simple = simpletcp
    simple.listen(serverAddressPort)
    pro_num = TCPNUM

# NetworkSetting
ifce_name, node_ip = simple.get_local_ifce_ip('10.0.')
# log_file(ifce_name).debug(f"ifce_name = {ifce_name}, node_ip = {node_ip}")

# Simple coin, setup network interface and process
app = SimpleCOIN(ifce_name=ifce_name, n_func_process=2, lightweight_mode=True)

pkts_payload = bytearray()
result = []

@app.main() # main function
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num, first, pkts_payload, svm_buffer
    
    if pro_num == TCPNUM:
        # No precess for TCP (not finished yet)
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

                # 这里使用多线程，因为如果使用单线程，那么在这里就会阻塞，导致后面的数据无法快速接收
                # 然而，这里有问题。pid=-1不使用多线程。
                simplecoin.submit_func(pid=-1, id='svm_service')
            else:
                print('*** header else!')
                pass

@app.func('svm_service')
def fastica_service(simplecoin: SimpleCOIN.IPC):
    global svm_buffer, svm_processed, _weight, _intercept, result          
    if svm_buffer.size() >= 1:

        joined_string:str = svm_buffer.pop()
        
        print(f"joined_string: {joined_string}")

        if "#" in joined_string:
            # the # is used to split the rows
            csv_list = joined_string.split("#")
            data = np.array([list(map(float, row.split(','))) for row in csv_list])
        else:
            # alone row
            data = [np.array([float(item) for item in joined_string.split(",")])]
        
        for csv_one_line in data:
            # svm process
            res_one_line = np.dot(csv_one_line, _weight) + _intercept
            res_final = 1 if res_one_line > 0 else 0
            result.append(res_final)

if __name__ == "__main__":
    app.run()
