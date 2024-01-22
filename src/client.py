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

##################################################
# Read x lines at a time from a csv file
READLINE = 10

##################################################


def read_and_format_csv(filename, chunk_size=10):
    with open(filename, 'r') as file:
        csv_reader = csv.reader(file)
        while True:
            # 每次处理 chunk_size 行数据
            chunk = []
            for row in islice(csv_reader, chunk_size):
                # 只取每行的最后16列，并每4列作为一组，用#连接
                formatted_row = '#'.join([','.join(row[-16:][i:i+4]) for i in range(0, 16, 4)])
                chunk.append(formatted_row)

            # 如果没有更多数据，退出循环
            if not chunk:
                break

            # 使用@连接处理过的行，然后yield
            yield '@'.join(chunk)

"""
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
"""

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

# log_file(ifce_name).debug(f"ifce_name = {ifce_name}, node_ip = {node_ip}")

app = SimpleCOIN(ifce_name=ifce_name, n_func_process=5, lightweight_mode=True)
serverAddressPort = ("10.0.0.30", 9999)
clientAddressPort = ("10.0.0.10", 9999)

for formatted_chunk in read_and_format_csv('test_file.csv', READLINE):
    print(formatted_chunk)

    # convert formatted_chunk to bytes and send it to the server
    formatted_chunk_bytes = str(formatted_chunk).encode()
    chunk_arr = chunk_handler.get_chunks_fc(formatted_chunk_bytes)
    
    print(f"chunk_arr: {len(chunk_arr)}")
    
    for chunk in chunk_arr:
            time.sleep(0.005)
            simple.sendto(chunk, serverAddressPort)

    if protocol == "tcp":
        simple.close()