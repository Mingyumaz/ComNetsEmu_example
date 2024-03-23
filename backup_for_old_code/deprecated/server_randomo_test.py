# 发送随机数据包到服务器，测试链路是否正确，以及能否处理数据包

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
app = SimpleCOIN(ifce_name = ifce_name, n_func_process = 1, lightweight_mode = True)

pred = []

# main function
@app.main()
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num, test_label, TOTALPKTS, RIGHTPKTS, start_time, end_time, RECEIVEPKT, pred

    if pro_num == UDPNUM:
        packet = simple.parse_af_packet(af_packet)
        if packet['Protocol'] == UDPNUM and packet['IP_src'] != node_ip:

            chunk = packet['Chunk']
            header = int(chunk[0])
            payload = chunk[1:]
            print("payload:", payload)

            if header == HEADER_INIT:
                print("ERROR ...")
            elif header == HEADER_FINISH:
                # print("NO =========== ERROR ...")
                if RECEIVEPKT == 0:
                    # Start
                    RECEIVEPKT = 1
                    start_time = time.time()
                    print("start to receive...")

                payload:str = payload.decode('utf-8')

                if payload == "end":
                    # END
                    # accuracy = RIGHTPKTS / TOTALPKTS
                    end_time = time.time()
                    processing_time = end_time - start_time
                    print(f"prediction is done, processing time: {processing_time} s with total pkts: {TOTALPKTS}")
                    RECEIVEPKT = 0
                else:
                    print(f"payload: {payload}")

                    TOTALPKTS += 1
                    # print(f"RIGHTPKTS: {RIGHTPKTS}, TOTALPKTS: {TOTALPKTS}")

if __name__ == "__main__":
    app.run()