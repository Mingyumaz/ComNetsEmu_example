import argparse
from simpleemu.simpleudp import simpleudp
from simpleemu.simpletcp import simpletcp
from simpleemu.simplecoin import SimpleCOIN
from scipy.stats import mode
from utils.packet import *
from utils.log import *
import time

#===============================================================================
TCPNUM = 6
UDPNUM = 17
RESULTFILENAME = 'result/rf_1_result.csv'
# 检查文件是否存在，如果存在，则删除
if os.path.exists(RESULTFILENAME):
    os.remove(RESULTFILENAME)

prediction = []
#===============================================================================
# network
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

@app.main()
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num, prediction

    if pro_num == UDPNUM:
        packet = simple.parse_af_packet(af_packet)
        if packet['Protocol'] == UDPNUM and packet['IP_src'] != node_ip:
            in_time = time.time()
            chunk = packet['Chunk']
            header = int(chunk[0])
            payload = chunk[1:]

            if header == HEADER_FINISH:
                total_str: str = payload.decode('utf-8')
                parts = total_str.split('$')
                pkts_ID = parts[0] # 数据包ID
                data_payload: str = parts[1] # 数据
                time_list: list = parts[2].split(',') # 时间戳
                worker_id = parts[3] # worker id

                time_list.append(in_time)
                time_list.append(time.time())

                # 最后的计算，加上截距
                if "&" in data_payload: # split the string by '@' and convert to float
                    rows = data_payload.split('&')

                    # 先转换为浮点数，再转换为整数
                    data_array = np.array([list(map(lambda x: int(float(x)), row.split(','))) for row in rows])

                    majority_vote = mode(data_array, axis=0)
                    final_predictions = majority_vote.mode
                    time_list.append(time.time())
                    time_list.append(time.time())
                    for res in final_predictions:
                        prediction.append([pkts_ID ,int(res), worker_id] + time_list)
                else:
                    print("____data_payload error with ", data_payload)

            elif header == TEST_BEGIN:
                # 开始和结束信号仅有时间戳，没有data，不需要切割处理
                time_list: list = payload.decode('utf-8').split(',') # 时间戳
                time_list.append(in_time)
                time_list.append(time.time())
                time_list.append(time.time())
                time_list.append(time.time())

                prediction.append([-1, -1, -1] + time_list)
                print("start to receive...")

            elif header == TEST_FINISH:
                print("finish ...")
                # 开始和结束信号仅有时间戳，没有data，不需要切割处理
                time_list: list = payload.decode('utf-8').split(',') # 时间戳
                time_list.append(in_time)
                time_list.append(time.time())
                time_list.append(time.time())
                time_list.append(time.time())

                prediction.append([-2, -2, -2] + time_list)

                df = pd.DataFrame(prediction)
                df.to_csv(RESULTFILENAME, mode='a', header=False, index=False)  # 不保存索引，不添加列名
                prediction = []

            else:
                print("____header error with ", header)

        
        if len(prediction) >= 1000:
            # 将data_list写入CSV文件
            print("write to csv with more than 1000 rows ...")
            df = pd.DataFrame(prediction)
            df.to_csv(RESULTFILENAME, mode='a', header=False, index=False)  # 不保存索引，不添加列名
            prediction = []

if __name__ == "__main__":
    app.run()