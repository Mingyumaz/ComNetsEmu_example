from simpleemu.simpleudp import simpleudp
from simpleemu.simplecoin import SimpleCOIN
from utils.packet import *
from utils.log import *
import argparse
import numpy as np
#===============================================================================
TCPNUM = 6
UDPNUM = 17
VNFNUM = 3
RECEIVEPKT = 0
TOTALPKTS = 0
RIGHTPKTS = 0
PROCESS_ROWS = 3 # 每次处理的行数
RESULTFILENAME = 'result/svm_baseline_result.csv'
# 检查文件是否存在，如果存在，则删除
if os.path.exists(RESULTFILENAME):
    os.remove(RESULTFILENAME)

_weight = [
    4.41166457, -1.96043454, 17.81108474, -4.61461225, -15.86521325,
    4.43944567, -6.11518636, 11.60370021, 11.25000529, -26.96724754,
    -19.65143135, 5.19897042, 0.20452559, 38.32446664, 10.39045664,
    -13.39039776
]
_intercept = -0.36835531

_weight = np.array(_weight)
_intercept = np.array([_intercept])
prediction = []
#===============================================================================

# # generate test label
# # datatrain_original = pd.read_csv('test_data.csv')
# datatrain_original = pd.read_csv('test_dataset.csv', nrows=50000)

# test_label = datatrain_original.iloc[:, -1]
# test_label = np.array(test_label)
# test_label = test_label.tolist()

#===============================================================================
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
app = SimpleCOIN(ifce_name = ifce_name, n_func_process = 3, lightweight_mode = True)

# 使用pandas在simplecoin中会出错，原因不清除，可能是因为simplecoin是多线程模式设计，pandas不支持多线程
# columns = ['result', 't_out_client', 't_in_vnf0', 't_out_vnf0', 't_in_vnf1', 't_out_vnf1', 't_in_vnf2', 't_out_vnf2', 't_in_server', 't_finish_server']
# df_timestamp= pd.DataFrame(columns=columns)

# main function
@app.main()
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num, _weight, _intercept, RECEIVEPKT, TOTALPKTS, RIGHTPKTS, VNFNUM, prediction

    if pro_num == UDPNUM:
        packet = simple.parse_af_packet(af_packet)
        if packet['Protocol'] == UDPNUM and packet['IP_src'] != node_ip:
            in_time = time.time()
            chunk = packet['Chunk']
            header = int(chunk[0])
            payload = chunk[1:]

            if header == HEADER_INIT:
                total_str: str = payload.decode('utf-8')
                parts = total_str.split('$', 1)
                
                # 将收到数据切分为数据和时间戳
                data_payload: str = parts[0] # 数据
                time_list: list = parts[1].split(',') # 时间戳

                time_list[2*VNFNUM + 1] = str(in_time)
                
                csv_list = data_payload.split("#")
                data = np.array([list(map(float, row.split(','))) for row in csv_list]) # 2 dimensional array, 16 columns and n rows

                for csv_one_line in data:

                    # SVM prediction process
                    decision_value = np.dot(csv_one_line, _weight.T) + _intercept
                    time_list[2*VNFNUM + 2] = str(time.time())
                    res_final = 1 if decision_value > 0 else 0

                    prediction.append([res_final] + time_list)

                    # new_row = [res_final] + time_list  # 创建新行
                    # new_series = pd.Series(new_row, index=df_timestamp.columns)  # 将新行转换为Series，确保列名对应
                    # df_timestamp = df_timestamp.append(new_series, ignore_index=True)  # 添加新行到DataFrame

                # time.sleep(0.0005) # add a delay to simulate the complex processing time

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
                print(prediction)

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

                # new_row = [2] + time_list  # 创建新行
                # new_series = pd.Series(new_row, index=df_timestamp.columns)  # 将新行转换为Series，确保列名对应
                # df_timestamp = df_timestamp.append(new_series, ignore_index=True)  # 添加新行到DataFrame

                # df_timestamp.to_csv('svm_baseline_result.csv', index=False)

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