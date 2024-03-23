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

TOTALPKTS = 0
RIGHTPKTS = 0

# _weight = [
#     4.41166457, -1.96043454, 17.81108474, -4.61461225, -15.86521325,
#     4.43944567, -6.11518636, 11.60370021, 11.25000529, -26.96724754,
#     -19.65143135, 5.19897042, 0.20452559, 38.32446664, 10.39045664,
#     -13.39039776
# ]
# _intercept = -0.36835531

# _weight = np.array(_weight)
# _intercept = np.array([_intercept])

# generate test label
# datatrain_original = pd.read_csv('test_data.csv')
datatrain_original = pd.read_csv('test_dataset.csv', nrows=50000)

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

# tcp/udp, tcp is not supported yet
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

# svm service function
@app.func('svm_service')
def svm_service(simplecoin: SimpleCOIN.IPC, payload):
    global _weight, _intercept, pred, RECEIVEPKT, start_time, TOTALPKTS, RIGHTPKTS

    if payload:
        if RECEIVEPKT == 0:
            # Start
            RECEIVEPKT = 1
            start_time = time.time()
            print("start to predict...")

        payload: str = payload.decode('utf-8')

        if payload == "end":
            # END
            accuracy = RIGHTPKTS / TOTALPKTS
            end_time = time.time()
            processing_time = end_time - start_time
            print(f"prediction is done, processing time: {processing_time} s with accuracy: {accuracy}")
            RECEIVEPKT = 0
        else:
            csv_list = payload.split("#")
            data = np.array([list(map(float, row.split(','))) for row in csv_list]) # 2 dimensional array, 16 columns and n rows

            result = []
            # 这里计算需要修改
            for csv_one_line in data:

                # SVM prediction process
                decision_value = np.dot(csv_one_line, _weight.T) + _intercept

                if decision_value > 0:
                    res_final = 1
                    pred.append(1)
                else:
                    res_final = 0
                    pred.append(0)

                result.append(res_final)

            # time.sleep(0.0005) # add a delay to simulate the complex processing time

            min_length = min(len(result), len(test_label) - TOTALPKTS)
            RIGHTPKTS += sum(1 for i in range(min_length) if result[i] == test_label[TOTALPKTS + i])
            TOTALPKTS += 5
            # print(f"RIGHTPKTS: {RIGHTPKTS}, TOTALPKTS: {TOTALPKTS}")
if __name__ == "__main__":
    app.run()