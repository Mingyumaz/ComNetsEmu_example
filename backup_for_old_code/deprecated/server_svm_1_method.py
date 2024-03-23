import argparse
from simpleemu.simpleudp import simpleudp
from simpleemu.simpletcp import simpletcp
from simpleemu.simplecoin import SimpleCOIN
from utils.packet import *
from utils.log import *
import time

#===============================================================================
TCPNUM = 6
UDPNUM = 17
VNFNUM = 3
RECEIVEPKT = 0
TOTALPKTS = 0
RIGHTPKTS = 0
PROCESS_ROWS = 3 # 每次处理的行数
RESULTFILENAME = 'result/svm_1_result.csv'
# 检查文件是否存在，如果存在，则删除
if os.path.exists(RESULTFILENAME):
    os.remove(RESULTFILENAME)

prediction = []

_intercept = -0.39625843
#===============================================================================

# # generate test label
# # datatrain_original = pd.read_csv('test_data.csv')
# datatrain_original = pd.read_csv('test_dataset.csv', nrows=50000)

# test_label = datatrain_original.iloc[:, -1]
# test_label = np.array(test_label)
# test_label = test_label.tolist()

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
    global pro_num, TOTALPKTS, RIGHTPKTS, RECEIVEPKT, VNFNUM, prediction

    if pro_num == UDPNUM:
        packet = simple.parse_af_packet(af_packet)
        if packet['Protocol'] == UDPNUM and packet['IP_src'] != node_ip:
            in_time = time.time()
            chunk = packet['Chunk']
            header = int(chunk[0])
            payload = chunk[1:]
            # RECEIVEPKT += 1

            if header == HEADER_FINISH:
                total_str: str = payload.decode('utf-8')
                parts = total_str.split('$', 1)

                # 将收到数据切分为数据和时间戳
                data_payload: str = parts[0] # 数据
                time_list: list = parts[1].split(',') # 时间戳

                time_list[2*VNFNUM + 1] = str(in_time)

                # 最后的计算，加上截距
                if "@" in data_payload: # split the string by '@' and convert to float
                    rows = data_payload.split('@')
                    for row in rows:
                        if "#" in row: # split the string by '#' and convert to float
                            data_value = row.split('#') # split the string by '#'
                            row_float = [float(i) for i in data_value] # convert to float
                        else:
                            row_float = [float(row)]
                        res_row = sum(row_float) + _intercept
                        time_list[2*VNFNUM + 2] = str(time.time())
                        res = 1 if res_row > 0 else 0
                        prediction.append([res] + time_list)
                else:
                    print("____data_payload error with ", data_payload)
                
                # min_length = min(len(result), len(test_label) - TOTALPKTS)
                # RIGHTPKTS += sum(1 for i in range(min_length) if result[i] == test_label[TOTALPKTS + i])
                # TOTALPKTS += PROCESS_ROWS
                # # print(f"RIGHTPKTS: {RIGHTPKTS}, TOTALPKTS: {TOTALPKTS}")

            elif header == TEST_BEGIN:
                # 开始和结束信号仅有时间戳，没有data，不需要切割处理
                time_list: list = payload.decode('utf-8').split(',') # 时间戳
                time_list[2*VNFNUM + 1] = str(in_time)
                time_list[2*VNFNUM + 2] = str(time.time())

                prediction.append([2] + time_list)

                # new_row = [2] + time_list  # 创建新行
                # new_series = pd.Series(new_row, index=df_timestamp.columns)  # 将新行转换为Series，确保列名对应
                # df_timestamp = df_timestamp.append(new_series, ignore_index=True)  # 添加新行到DataFrame
                # print(df_timestamp)
                # NO process, only forward
                print("start to receive...")
                # print(prediction)

            elif header == TEST_FINISH:
                print("finish ...")
                # 开始和结束信号仅有时间戳，没有data，不需要切割处理
                time_list: list = payload.decode('utf-8').split(',') # 时间戳
                time_list[2*VNFNUM + 1] = str(in_time)
                time_list[2*VNFNUM + 2] = str(time.time())

                prediction.append([2] + time_list)

                df = pd.DataFrame(prediction)
                df.to_csv(RESULTFILENAME, mode='a', header=False, index=False)  # 不保存索引，不添加列名
                prediction = []

                # print("finish ...")
                # print(payload)
                # accuracy = RIGHTPKTS / TOTALPKTS
                # end_time = time.time()
                # processing_time = end_time - start_time
                # print(f"prediction is done, processing time: {processing_time} s with {TOTALPKTS} packets with accuracy: {accuracy}")
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