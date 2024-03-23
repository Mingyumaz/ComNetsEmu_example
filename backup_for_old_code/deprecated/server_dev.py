from simpleemu.simpleudp import simpleudp
from simpleemu.simplecoin import SimpleCOIN
from utils.packet import *
from utils.log import *
import argparse

TCPNUM = 6
UDPNUM = 17

RECEIVEPKT = 0
start_time = None
end_time = None

_weight = [
    4.4673759, -1.9508139, 18.2929355, -4.59865486, -15.89973784,
    4.45173673, -6.66900071, 11.41212687, 12.09920352, -27.93013163,
    -20.25551204, 5.15629348, -0.51542374, 39.24373589, 11.14313096,
    -13.25246068
]
_intercept = -0.39625849

_weight = np.array(_weight)
_intercept = np.array([_intercept])

# generate test label
datatrain_original = pd.read_csv('test_data.csv')
# datatrain_original = pd.read_csv('test_data.csv', nrows=500000)

test_label = datatrain_original.iloc[:, -1]
test_label = np.array(test_label)
test_label = test_label.tolist()

# network setting
serverAddressPort = ("10.0.0.30", 9999)
clientAddressPort = ("10.0.0.10", 9999)

# parse args
parser = argparse.ArgumentParser(description="Using TCP or UDP")
parser.add_argument("--protocol", "-p", type=str, choices=["tcp", "udp", "t", "u"], default="udp",
                    help="choosing protocol, tcp/t or udp/u(default udp)")
args = parser.parse_args() # to parse command line arguments to determine which protocol to use

if args.protocol in ["udp", "u"]:
    protocol = "udp"
    simple = simpleudp
    pro_num = UDPNUM

# network setting
ifce_name, node_ip = simple.get_local_ifce_ip('10.0.')
# log_file(ifce_name).debug(f"ifce_name = {ifce_name}, node_ip = {node_ip}")

# simple coin, setup network interface and process
app = SimpleCOIN(ifce_name = ifce_name, n_func_process = 3, lightweight_mode = True)

pkts_payload = bytearray() # used to store the payload of packets
result = []
pred = []

# main function
@app.main()
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num, first, pkts_payload, svm_buffer

    if pro_num == UDPNUM:
        packet = simple.parse_af_packet(af_packet)
        if packet['Protocol'] == UDPNUM and packet['IP_src'] != node_ip:
            pkts_payload = packet['Chunk']
            simplecoin.submit_func(pid=2, id='svm_service', args=(pkts_payload, )) # pid=-1 means use single-threading

@app.func('svm_service')
def svm_service(simplecoin: SimpleCOIN.IPC, payload):
    global _weight, _intercept, pred, RECEIVEPKT, start_time

    if payload:
        if RECEIVEPKT == 0:
            # Start
            RECEIVEPKT = 1
            start_time = time.time()
            print("start to predict...")

        payload: str = payload.decode('utf-8')

        if payload == "end":
            end_time = time.time()
            processing_time = end_time - start_time
            print(f"prediction is done, processing time: {processing_time} s with accuracy: {accuracy}")
            RECEIVEPKT = 0

        else:
            csv_list = payload.split("#")
            data = np.array([list(map(float, row.split(','))) for row in csv_list]) # 2 dimensional array, 16 columns and n rows

            result = []
            for csv_one_line in data:

                # SVM prediction process
                decision_value = np.dot(csv_one_line, _weight.T) + _intercept
                res_final = 1 if decision_value > 0 else 0
                pred.append(res_final)
                result.append(res_final)

            # time.sleep(0.0005) # add a delay to simulate the complex processing time
        accurary = sum(1 for i in range(len(result)) if result[i] == test_label[i])/len(result)
        accurary *= 100
        print(f"accuracy: {accurary} %")
        # print(f"RIGHTPKTS: {RIGHTPKTS}, TOTALPKTS: {TOTALPKTS}")

if __name__ == "__main__":
    app.run()