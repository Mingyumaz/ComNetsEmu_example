import logging
from tabnanny import filename_only
import time
import csv
import os
import pandas as pd

index_dict_loc = {}

def gen_index_dict_loc(n_vnf):
    global index_dict_loc
    for i in range(n_vnf + 2):  # 加2是因为 "client-s0" 和 "server-sX" 两个特殊的名称
        if i == 0:
            index_dict_loc["client-s0"] = 0
        elif i == n_vnf + 1:
            index_dict_loc[f"server-s{n_vnf-1}"] = i
        else:
            index_dict_loc[f"vnf{i-1}-s{i-1}"] = i
    return index_dict_loc

time_str = time.strftime("%Y-%m-%d-%H_%M_%S", time.localtime())


def log_cmd():
    log_cmd = logging.getLogger("console-logger")
    log_cmd.handlers.clear()
    stream_handler = logging.StreamHandler()
    log_cmd.addHandler(stream_handler)
    log_cmd.setLevel(logging.INFO)
    return log_cmd


def log_file(ifce_name: str):
    log_file = logging.getLogger("file-logger")
    log_file.handlers.clear()
    file_name = ifce_name + "_" + time_str + ".log"
    file_handler = logging.FileHandler(file_name)
    file_handler.setFormatter(logging.Formatter(
        "%(filename)s | %(asctime)s | %(message)s"))
    log_file.addHandler(file_handler)
    log_file.setLevel(logging.DEBUG)
    return log_file




def delLastLine(path):
    with open(path, "rb+") as f:
        lines = f.readlines()  # 读取所有行
        last_line = lines[-1]  # 取最后一行
        for i in range(len(last_line) + 2):  ##愚蠢办法，但是有效
            f.seek(-1, os.SEEK_END)
            f.truncate()
        f.close()
        f = open(path, "a")
        f.write('\r\n')
        f.close()

    return