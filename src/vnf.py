import argparse
from simpleemu.simpleudp import simpleudp
from simpleemu.simpletcp import simpletcp
from simpleemu.simplecoin import SimpleCOIN
from utils.packet import *
from utils.log import *

# Network
serverAddressPort = ("10.0.0.30", 9999)
clientAddressPort = ("10.0.0.10", 9999)

# parse args
parser = argparse.ArgumentParser(description="Using TCP or UDP")
parser.add_argument("--protocol", "-p", type=str, choices=["tcp", "udp", "t", "u"], default="udp",
                    help="choosing protocol, tcp/t or udp/u(default udp)")
args = parser.parse_args()

# tcp/udp
if args.protocol in ["udp", "u"]:
    protocol = "udp"
    simple = simpleudp
    pro_num = 17
else:
    protocol = "tcp"
    simple = simpletcp
    pro_num = 6

# network setting
ifce_name, node_ip = simple.get_local_ifce_ip('10.0')

# Simple coin
app = SimpleCOIN(ifce_name=ifce_name, n_func_process=1, lightweight_mode=True)


@app.main()
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num
    packet = simple.parse_af_packet(af_packet)
    # check if the packet is UDP and not from the server
    if packet['Protocol'] == pro_num and packet['IP_src'] != node_ip:
            # parse the packet and calculate the square
            random_number = int(packet['Chunk'].decode())
            squared_number = random_number ** 2
            print(f"Received number: {random_number}, Squared: {squared_number}")

            # prepare the new packet and send it to the server
            squared_number_bytes = str(squared_number).encode()  # turn the squared number into bytes
            af_packet_chunk = chunk_handler.get_chunks_fc(squared_number_bytes)
            af_packet = b''.join(af_packet_chunk) # join the chunks
            print("forwarding")
            simplecoin.forward(af_packet)

app.run()