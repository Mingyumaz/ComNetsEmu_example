from simpleemu.simpleudp import simpleudp
from simpleemu.simplecoin import SimpleCOIN
from utils.packet import *
from utils.log import *
import argparse

TCPNUM = 6
UDPNUM = 17

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

            if header == HEADER_INIT:
                print("payload:", payload)
                new_payload = bytes([HEADER_FINISH]) +  str(payload).encode()
                simple.sendto(new_payload, clientAddressPort)
            else:
                print("Error: header is not 0")


if __name__ == "__main__":
    app.run()