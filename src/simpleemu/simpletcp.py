# -*- coding: utf-8 -*-

# @Author: Shenyunbin
# @email : yunbin.shen@mailbox.tu-dresden.de / shenyunbin@outlook.com
# @create: 2021-04-01
# @modify: 2021-04-01
# @desc. : [description]

import socket
from typing import Tuple

class SimpleTCP():
    def __init__(self, BUFFER_SIZE: int = 4096) -> None:
        self.BUFFER_SIZE = BUFFER_SIZE
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connections = {}
        pass

    def connect(self, dst_addr: Tuple[str, int]):
        # create connection to destination
        if dst_addr not in self.connections:
            self.client.connect(dst_addr)
            self.connections[dst_addr] = self.client

    def sendto(self, data: bytes, dst_addr: Tuple[str, int]):
        # checking if connection is created
        if dst_addr not in self.connections:
            self.connect(dst_addr)

        # using connection send data
        self.connections[dst_addr].sendall(data)

    # listen for incoming connections
    def listen(self, dst_addr: Tuple[str, int], backlog: int = 5):
        _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _socket.bind(dst_addr)
        _socket.listen(backlog)
        self.connections[dst_addr] = _socket

    # accept a connection
    def accept(self, dst_addr: Tuple[str, int]):
        conn, addr = self.connections[dst_addr].accept()
        return conn, addr

    # recv tcp packet
    def recv(self, conn):
        data = conn.recv(self.BUFFER_SIZE)
        return data

    # close the socket
    def close(self):
        self.client.close()
        for _socket in self.connections.values():
            _socket.close()

    # Other methods (e.g., parse_af_packet, get_local_ifce_ip) remain unchanged
    def parse_af_packet(self, af_packet: bytes, frame_len: int = 0):
        if frame_len > 14:
            af_packet = af_packet[:frame_len]
        packet = {}
        packet['Raw'] = af_packet
        data = af_packet[14:]  # 去掉以太网帧头

        # IP 头部解析
        packet['Protocol'] = data[9]  # IP协议号
        packet['IP_src'] = '.'.join(map(str, data[12:16]))
        packet['IP_dst'] = '.'.join(map(str, data[16:20]))

        # TCP 头部解析
        packet['Port_src'] = int.from_bytes(data[20:22], 'big')
        packet['Port_dst'] = int.from_bytes(data[22:24], 'big')
        packet['Seq_num'] = int.from_bytes(data[24:28], 'big')
        packet['Ack_num'] = int.from_bytes(data[28:32], 'big')
        header_len = (data[32] >> 4) * 4  # TCP头部长度
        packet['Chunk'] = data[20 + header_len:]

        return packet
    
    # get ifce name and node ip automatically
    def get_local_ifce_ip(self, ip_prefix: str):
        from subprocess import Popen, PIPE
        ifconfig_output = Popen('ifconfig', stdout=PIPE).stdout.read()
        for paragraph in ifconfig_output.split(b'\n\n'):
            paragraph = paragraph.split()
            if len(paragraph)>6 and len(paragraph[0])>1:
                ifce_name = paragraph[0][:-1].decode("utf-8")
                ip = paragraph[5].decode("utf-8")
                if ip_prefix in ip:
                    return ifce_name,ip
        raise ValueError('ip not detected!')


# Usage example
simpletcp = SimpleTCP()
