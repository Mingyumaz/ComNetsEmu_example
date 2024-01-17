import time
import argparse
import csv

from simpleemu.simpleudp import simpleudp
from simpleemu.simpletcp import simpletcp
# from simpleemu.simplecoin import SimpleCOIN

from utils.log import *
from utils.packet import *
from itertools import islice

def read_and_format_csv(filename, chunk_size=10):
    with open(filename, 'r') as file:
        csv_reader = csv.reader(file)
        while True:
            # 仅保留每一行的最后16个元素
            chunk = [','.join(row[-16:]) for row in islice(csv_reader, chunk_size)]
            if not chunk:
                break
            yield '#'.join(chunk)

# parse args
parser = argparse.ArgumentParser(description="Using TCP or UDP")
parser.add_argument("--protocol", "-p", type=str, choices=["tcp", "udp", "t", "u"], default="udp",
                    help="choosing protocol, tcp/t or udp/u(default udp).")
args = parser.parse_args()

# tcp/udp
if args.protocol in ["udp", "u"]:
    protocol = "udp"
    simple = simpleudp
else:
    protocol = "tcp"
    simple = simpletcp

# network setting
ifce_name, node_ip = simple.get_local_ifce_ip('10.0')

# app = SimpleCOIN(ifce_name=ifce_name, n_func_process=5, lightweight_mode=True)
serverAddressPort = ("10.0.0.30", 9999) # Server address
clientAddressPort = ("10.0.0.10", 9999) # Client address
    
# using generator, read 10 lines at a time, then send to server
for formatted_chunk in read_and_format_csv('test_file.csv', 10):

    # Convert random number to bytes and send it to the server
    formatted_chunk_bytes = str(formatted_chunk).encode()

    chunk_arr = chunk_handler.get_chunks_fc(formatted_chunk_bytes)

    for chunk in chunk_arr:
        time.sleep(0.1)
        simple.sendto(chunk, serverAddressPort)
