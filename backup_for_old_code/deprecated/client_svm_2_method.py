import time
import argparse
import csv
from simpleemu.simpleudp import simpleudp
from simpleemu.simpletcp import simpletcp
from simpleemu.simplecoin import SimpleCOIN
from utils.log import *
from utils.packet import *
from itertools import islice
#===============================================================================
# initial parameters
TCPNUM = 6
UDPNUM = 17

STATUS_SEND = False

MAXLINE = 1 # 最大发送循环次数，发送行数等于MAXLINE*PROCESS_ROWS
CURRENTLINE = 0 # 当前行数
PROCESS_ROWS = 3 # 每次处理的行数
SEND_INTERVAL = 0.001 # 数据包发送间隔
VNFNUM = 3

RESULTFILENAME = 'result/svm_2_result.csv'
# 检查文件是否存在，如果存在，则删除
if os.path.exists(RESULTFILENAME):
    os.remove(RESULTFILENAME)

prediction = []
#===============================================================================
def read_and_format_csv(filename, chunk_size=1):
    with open(filename, 'r') as file:
        csv_reader = csv.reader(file)
        while True:
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
    pro_num = UDPNUM
else:
    protocol = "tcp"
    simple = simpletcp
    pro_num = TCPNUM

# app = SimpleCOIN(ifce_name=ifce_name, n_func_process=5, lightweight_mode=True)
serverAddressPort = ("10.0.0.30", 9999)
clientAddressPort = ("10.0.0.10", 9999)

# network setting
ifce_name, node_ip = simple.get_local_ifce_ip('10.0')

app = SimpleCOIN(ifce_name=ifce_name, n_func_process=2, lightweight_mode=True)

#===============================================================================
@app.main()
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num, STATUS_SEND, prediction
    if not STATUS_SEND:
        STATUS_SEND = True
        simplecoin.submit_func(pid=1, id='send_service')

    packet = simple.parse_af_packet(af_packet)
    if packet['Protocol'] == pro_num and packet['IP_src'] != node_ip:
        in_time = time.time()
        chunk = packet['Chunk']
        header = int(chunk[0])
        payload = chunk[1:]
        
        # feedback from server [header + result + $ + time_list]
        if header == HEADER_FEEDBACK:
            total_str: str = payload.decode('utf-8')
            parts = total_str.split('$', 1)
            
            # 将收到数据切分为数据和时间戳
            result_payload: list = parts[0].split(',') # result
            time_list: list = parts[1].split(',') # 时间戳
            time_list.append(str(in_time))
            
            for res in result_payload:
                prediction.append([res] + time_list)
        elif header == TEST_BEGIN:
            # 开始和结束信号仅有时间戳，没有data，不需要切割处理
            time_list: list = payload.decode('utf-8').split(',') # 时间戳
            time_list.append(str(in_time))

            prediction.append([2] + time_list)
        elif header == TEST_FINISH:
            # 开始和结束信号仅有时间戳，没有data，不需要切割处理
            time_list: list = payload.decode('utf-8').split(',') # 时间戳
            time_list.append(str(in_time))

            prediction.append([2] + time_list)
            df = pd.DataFrame(prediction)
            df.to_csv(RESULTFILENAME, mode='a', header=False, index=False)  # 不保存索引，不添加列名
            prediction = []
        else:
            print("header error ...")

        if len(prediction) >= 1000:
                # 将data_list写入CSV文件
                print("write to csv with more than 1000 rows ...")
                df = pd.DataFrame(prediction)
                df.to_csv(RESULTFILENAME, mode='a', header=False, index=False)  # 不保存索引，不添加列名
                prediction = []


@app.func('send_service')
def send_service(simplecoin: SimpleCOIN.IPC):
    print("send_service start ...")
    global SEND_INTERVAL, MAXLINE, PROCESS_ROWS, CURRENTLINE, VNFNUM
    
    time_list = [0 for _ in range(2*VNFNUM+3)]

    # 1. 发送数据
    for formatted_chunk in read_and_format_csv('test_data_feature.csv', PROCESS_ROWS):

        if CURRENTLINE == MAXLINE:
            break
        CURRENTLINE += 1
        payload = bytes([HEADER_INIT]) +  str(formatted_chunk).encode() # 未处理 HEADER_INIT
        time_list[0] = str(time.time())
        payload_timestamp = ("$" + ','.join(map(str, time_list))).encode()

        time.sleep(SEND_INTERVAL)
        # simple.sendto(payload, serverAddressPort) # 仅发送数据，不发送时间
        simple.sendto(payload + payload_timestamp, serverAddressPort) # 发送数据和时间
    
    # 2. 发送结束信号
    time.sleep(SEND_INTERVAL)
    end_time = time.time()
    time_list[0] = str(end_time)
    end_payload = bytes([TEST_FINISH]) + (','.join(map(str, time_list))).encode()
    simple.sendto(end_payload, serverAddressPort)
    
    print("send_service end ...")


# 先发一个起跳包，不然可能client没有收到包就不会进入main函数，也就无法进入send_service
# 加入测试时间戳，用于测试数据包发送时间，时间随数据包一起发送。
# 数据和时间通过"$"分隔，数据之间通过","或者""分隔。
time_list = [0 for _ in range(2*VNFNUM+3)]
start_time = time.time()
time_list[0] = str(start_time)
begin_payload = bytes([TEST_BEGIN]) + (','.join(map(str, time_list))).encode()
simple.sendto(begin_payload, serverAddressPort)

time.sleep(SEND_INTERVAL)

# 2.run
app.run()


# # TIME
# # 加入测试时间戳，用于测试数据包发送时间，时间随数据包一起发送。
# # 数据和时间通过"$"分隔，数据之间通过","或者""分隔。
# time_list = [0 for _ in range(2*VNFNUM+3)]

# # 1.发送开始信号
# start_time = time.time()
# time_list[0] = str(start_time)
# begin_payload = bytes([TEST_BEGIN]) + (','.join(map(str, time_list))).encode()
# simple.sendto(begin_payload, serverAddressPort)

# # 2.发送数据
# for formatted_chunk in read_and_format_csv('test_data_feature.csv', PROCESS_ROWS):

#     if CURRENTLINE == MAXLINE:
#         break
#     CURRENTLINE += 1
#     payload = bytes([HEADER_INIT]) +  str(formatted_chunk).encode() # 未处理 HEADER_INIT
#     time_list[0] = str(time.time())
#     payload_timestamp = ("$" + ','.join(map(str, time_list))).encode()

#     time.sleep(SEND_INTERVAL)
#     # simple.sendto(payload, serverAddressPort) # 仅发送数据，不发送时间
#     simple.sendto(payload + payload_timestamp, serverAddressPort) # 发送数据和时间

# # 3.发送结束信号
# time.sleep(SEND_INTERVAL)
# end_time = time.time()
# time_list[0] = str(end_time)
# end_payload = bytes([TEST_FINISH]) + (','.join(map(str, time_list))).encode()
# simple.sendto(end_payload, serverAddressPort)

# # 4.打印发送数量等信息
# print(f"Send {CURRENTLINE*PROCESS_ROWS + 2} lines data, with 1 begin and 1 end message.")