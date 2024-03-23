import numpy as np
import argparse
from simpleemu.simpleudp import simpleudp
from simpleemu.simpletcp import simpletcp
from simpleemu.simplecoin import SimpleCOIN
from utils.packet import *
from utils.log import *
from joblib import load

#===============================================================================
# init paratmeters
TCPNUM = 6
UDPNUM = 17

TOTALNUM = 4 # 总共有4列（16列分为4组）数据
# VNF1PROCESSNUM = [0,1,2,3],目前是16列分为4组，
# 这里给VNF1处理0,1列，VNF2处理2列，VNF3处理3列
VNF1PROCESSNUM = [0,1]
VNF2PROCESSNUM = [2]
VNF3PROCESSNUM = [3]
current_vnf = [] # 标记当前是哪个VNF在处理数据


_weight = np.array([
    [4.46737612, -1.95081422, 18.29293572, -4.5986548],
    [-15.89973802, 4.45173662, -6.66900044, 11.41212648],
    [12.09920262, -27.9301321, -20.2555121, 5.15629297],
    [-0.51542267, 39.2437361, 11.1431311, -13.25246067]
])


# _weight = [
#     [4.46737612, -1.95081422, 18.29293572, -4.5986548],
#     [-15.89973802, 4.45173662, -6.66900044, 11.41212648],
#     [12.09920262, -27.9301321, -20.2555121, 5.15629297],
#     [-0.51542267, 39.2437361, 11.1431311, -13.25246067]
# ]
_intercept = -0.39625843
#===============================================================================
# network setting
serverAddressPort = ("10.0.0.30", 9999)
clientAddressPort = ("10.0.0.10", 9999)

# parse args
parser = argparse.ArgumentParser(description="Using TCP or UDP")
parser.add_argument("--protocol", "-p", type=str, choices=["tcp", "udp", "t", "u"], default="udp",
                    help="choosing protocol, tcp/t or udp/u (default udp)")
parser.add_argument("--num", "-n", type=int, choices=[1, 2, 3], default=1,
                    help="which number is this switch. 1, 2 or 3 (default 1)")
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

num = args.num # set the function number of the vnf
if   num == 1:
    current_vnf = VNF1PROCESSNUM
elif num == 2:
    current_vnf = VNF2PROCESSNUM
elif num == 3:
    current_vnf = VNF3PROCESSNUM

ifce_name, node_ip = simple.get_local_ifce_ip('10.0')
# simple coin
app = SimpleCOIN(ifce_name=ifce_name, n_func_process=1, lightweight_mode=True)

@app.main()
def main(simplecoin: SimpleCOIN.IPC, af_packet: bytes):
    global pro_num, current_vnf

    if pro_num == UDPNUM:
        packet = simple.parse_af_packet(af_packet)
        if packet['Protocol'] == UDPNUM and packet['IP_src'] != node_ip:
            in_time = time.time() # 1.接受数据时间戳
            chunk = packet['Chunk']
            header = int(chunk[0])
            payload = chunk[1:]

            if header == HEADER_INIT:
                # 1.需要被处理的数据包
                total_str: str = payload.decode('utf-8')
                parts = total_str.split('$', 1)

                # 将收到数据切分为数据和时间戳
                data_payload: str = parts[0] # 数据
                time_list: list = parts[1].split(',') # 时间戳
                time_list[2*num-1] = str(in_time)

                result = ""

                rows = data_payload.split('@')# 按@分割得到每一行
                nested_list = []

                for row in rows:
                    parts = row.split('#') # 按#分割得到四个部分
                    row_list = [np.array(part.split(','), dtype=float) for part in parts] # 将每个部分转换为NumPy数组，并加入到行列表中
                    nested_list.append(row_list) # 将行列表加入到最终列表中

                # print(f"nested_list: {nested_list}")

                # (为下面这个循环处理解释) 这里收到的数据将会是这样：
                #
                # 计划让VNFx可以处理任意列的数据，而不是固定的，可以随意选择。因为数据按列分组，然后计算。
                #
                # VNF1 中 (假设收到数据有3行，当然几行都可能)，他们会是这样(其实数据只是一行，
                # 这里分行看会清楚一些)：
                #--- 1, 2, 3, 4 # 5, 6, 7, 8 # 9, 10, 11, 12 # 13, 14, 15, 16 @
                #--- 1, 2, 3, 4 # 5, 6, 7, 8 # 9, 10, 11, 12 # 13, 14, 15, 16 @
                #--- 1, 2, 3, 4 # 5, 6, 7, 8 # 9, 10, 11, 12 # 13, 14, 15, 16 @ ......
                #--- 那么，在设定的 VNF1PROCESSNUM (目前我设定[0, 1], 代表第一个竖列分区和第二个竖列分区) 中
                # ，我们只需要处理第一列和第二列，即：
                #--- 1, 2, 3, 4 # 5, 6, 7, 8 @
                #--- 1, 2, 3, 4 # 5, 6, 7, 8 @
                #--- 1, 2, 3, 4 # 5, 6, 7, 8 @
                # 这四行数据，然后进行运算，得到结果，再将结果和第三列和第四列拼接起来，即：
                #--- value # value # 9, 10, 11, 12 # 13, 14, 15, 16 @
                #--- value # value # 9, 10, 11, 12 # 13, 14, 15, 16 @
                #--- value # value # 9, 10, 11, 12 # 13, 14, 15, 16 @ ......
                # 最后，发送出去给VNF2.
                #
                # 那么如果我设定VNF1PROCESSNUM处理第一列和第三列，那么就是：VNF1PROCESSNUM=[0, 2]
                # 那么就是：
                #--- value # 5, 6, 7, 8 # value # 13, 14, 15, 16 @
                #--- value # 5, 6, 7, 8 # value # 13, 14, 15, 16 @
                #--- value # 5, 6, 7, 8 # value # 13, 14, 15, 16 @ ......
                # 然后发送给VNF2, 以此类推。
                for csv_one_line in nested_list:
                    # svm process
                    temp = ""  # 确保在循环开始时初始化result
                    for i in range(TOTALNUM):
                        if i in current_vnf:
                            res_one_line = np.dot(csv_one_line[i], _weight[i])
                            temp += str(res_one_line) + "#"
                        else:
                            temp += ','.join(map(str, csv_one_line[i])) + "#"

                        # print("-------------")
                        # print(temp)
                        # print("-------------")
                    result += temp[:-1] + "@" # add @ to split the rows in last columns
                result = result[:-1] # remove the last @

                # print(f"result: {result}")

                if current_vnf == VNF3PROCESSNUM:
                    tag_header = HEADER_FINISH
                else:
                    tag_header = HEADER_INIT

                time_list[2*num] = str(time.time()) # 2.准备发送数据时间戳
                new_payload = (result + "$" + ','.join(map(str, time_list))).encode()
                # print("new_payload: ", new_payload)
                # 发送数据
                simplecoin.sendto(bytes([tag_header]) + new_payload, serverAddressPort)

            elif header == TEST_BEGIN or header == TEST_FINISH :
                # 2.开始或结束标志
                time_list: list = payload.decode('utf-8').split(',') # 时间戳
                time_list[2*num-1] = str(in_time)
                # NO process, only forward

                time_list[2*num] = str(time.time()) # 2.准备发送数据时间戳
                new_payload = (','.join(map(str, time_list))).encode()

                # 发送数据
                simplecoin.sendto(bytes([header]) + new_payload, serverAddressPort)
                print("Begin or end signal...")

            else:
                # 3.错误的header
                print("____header error with ", header)

if __name__ == "__main__":
    app.run()