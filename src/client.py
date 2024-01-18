import time
import argparse

import random
import csv
import os
from simpleemu.simpleudp import simpleudp
from simpleemu.simpletcp import simpletcp
from simpleemu.simplecoin import SimpleCOIN

from utils.log import *
from utils.packet import *
from itertools import islice

# read csv file and format as string
def read_and_format_csv(filename, chunk_size = 10):
    with open(filename, 'r') as file:
        csv_reader = csv.reader(file)
        while True:
            # only save the last 16 columns
            chunk = [','.join(row[-16:][i:i+4]) for row in islice(csv_reader, chunk_size) for i in range(0, 16, 4)]
            if not chunk:
                break
            yield '#'.join(chunk)

# parse args
parser = argparse.ArgumentParser(description="using TCP or UDP")
parser.add_argument("--protocol", "-p", type=str, choices=["tcp", "udp", "t", "u"], default="udp",
                    help="choosing protocol, tcp/t or udp/u(default udp).")
args = parser.parse_args()

# TCP/UDP
if args.protocol in ["udp", "u"]:
    protocol = "udp"
    simple = simpleudp
else:
    protocol = "tcp"
    simple = simpletcp

# network setting
ifce_name, node_ip = simple.get_local_ifce_ip('10.0')

log_file(ifce_name).debug(f"ifce_name = {ifce_name}, node_ip = {node_ip}")
app = SimpleCOIN(ifce_name=ifce_name, n_func_process=5, lightweight_mode=True)
serverAddressPort = ("10.0.0.30", 9999)
clientAddressPort = ("10.0.0.10", 9999)

# using the generator, read 10 lines at a time and send to server
for formatted_chunk in read_and_format_csv('test_file.csv', 5): # the csv file has 21 lines, and 5 lines per chunk
    print(formatted_chunk)

    # convert formatted_chunk to bytes and send it to the server
    formatted_chunk_bytes = str(formatted_chunk).encode()
    chunk_arr = chunk_handler.get_chunks_fc(formatted_chunk_bytes) # get chunks
    print(f"chunk_arr: {len(chunk_arr)}")
    for chunk in chunk_arr:
            time.sleep(0.005)
            simple.sendto(chunk, serverAddressPort)

    if protocol == "tcp":
        simple.close()