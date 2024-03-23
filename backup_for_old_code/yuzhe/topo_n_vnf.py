from email.header import Header
import argparse

#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
'''
@File    :   topo_n_vnf.py
@Time    :   2022/03/19 20:28:59
@Author  :   Jiakang Weng
@Version :   1.0
@Contact :   jiakang.weng@mailbox.tu-dresden.de
@License :   (C)Copyright 2021-2022
@Desc    :   Yoho topo n vnf
'''
# you can check this link to know how list(map(lambda)) works:
# ------------------------------------------------------------------
# | https://blog.csdn.net/stay_foolish12/article/details/107160831 |
# ------------------------------------------------------------------


# here put the import lib
from simpleemu.simpletopo import SimpleTopo

# global value & function
n_vnf = 3

def set_args(args):
    global n_vnf
    n_vnf = args.vnf

if __name__ == "__main__":
    # argparse setting
    parser = argparse.ArgumentParser(description="Topo vnf setting.")

    parser.add_argument(
        "--vnf",
        type=int,
        default=3,
        help="The number of vnfs."
    )

    parser.set_defaults(func=set_args)
    args = parser.parse_args()
    args.func(args)
    print("*** VNF Number:",n_vnf)

    # start SimpleTopo
    topo = SimpleTopo()

    topo.addController(node_name='c0')
    
    # client分配3个cpu核心，server分配3个cpu核心
    topo.addHostNode(node_name='client', 
                     ip='10.0.0.10', 
                     dimage='simple_dev:1.3', 
                     volume=None,
                     docker_args={"cpuset_cpus": '0-2',
                                  "cpu_period": 100000,
                                  'cpu_quota': -1}) # `cpu_quota` is the percentage of the CPU, 100000 is 100%
    topo.addHostNode(node_name='server', 
                     ip='10.0.0.30', 
                     dimage='simple_dev:1.3', 
                     volume=None,
                     docker_args={"cpuset_cpus": '3-5',
                                  "cpu_period": 100000,
                                  'cpu_quota': -1}) # `cpu_quota` is the percentage of the CPU, 100000 is 100%
    
    # # server 和 client 共同分配占用2个cpu核心，？分配不均可能。
    # topo.addHostNodes(node_names=['client', 'server'],
    #                     ip_prefix='10.0.0.', ip_suffixes=['10', '30'],
    #                     dimage='simple_dev:1.3', volume=None,
    #                     docker_args={"cpuset_cpus": '0-1', 
    #                                  "cpu_period": 100000, 
    #                                  'cpu_quota': -1}) # `cpu_quota` is the percentage of the CPU, 100000 is 100%
    
    # 每个vnf占用1个cpu核心，太少了分配。
    # for i in range(n_vnf):
    #     topo.addHostNodes(node_names=['vnf'+ str(i)],
    #                         ip_prefix='10.0.0.', ip_suffixes=[str(i+11)],
    #                         dimage='simple_dev:1.0', volume=None,
    #                         docker_args={"cpuset_cpus": str(i+2), 
    #                                      "cpu_period": 100000,
    #                                      'cpu_quota': -1}) # `cpu_quota` is the percentage of the CPU, 100000 is 100%

    # 每个vnf占用3个cpu核心，测试发现可能CPU在3个核心上，SVM不会吃满（单CPU会80%占用）
    for i in range(n_vnf):
        topo.addHostNodes(node_names=['vnf'+ str(i)],
                            ip_prefix='10.0.0.', ip_suffixes=[str(i+11)],
                            dimage='simple_dev:1.0', volume=None,
                            docker_args={"cpuset_cpus": (str(i*3+6) + "-" + str(i*3+8)), 
                                         "cpu_period": 100000,
                                         'cpu_quota': -1}) # `cpu_quota` is the percentage of the CPU, 100000 is 100%


    topo.addSwitchNodes(node_names=list(
        map(lambda x: 's'+str(x), range(n_vnf))))
    
    # create links, `bw` is bandwith, unit of bandwith is 'Mbit/s'
    # topo.addLinks(links=['client - '+''.join(list(map(lambda x: 's'+str(x)+'-', range(n_vnf))))+'server'] +
    #                 list(map(lambda x: 's'+str(x)+'-'+'vnf'+str(x), range(n_vnf))), bw=1000, delay='10ms', use_htb=True)
    
    # 这样会为每条链路设置延迟，但是我们不希望vnf和switch之间有延迟。
    # topo.addLinks(links=['client - s0-s1-s2-server'] + ['s0-vnf0', 's1-vnf1', 's2-vnf2'], 
    #               bw=1000, 
    #               delay='10ms', 
    #               use_htb=True)
    
    # 首先，为需要设置延迟的链路调用 addLinks 方法
    topo.addLinks(links=['client - s0-s1-s2-server'], 
                bw=1000, 
                delay='10ms', 
                use_htb=True)

    # 然后，为不需要设置延迟的链路调用 addLinks 方法，不指定 delay 参数
    topo.addLinks(links=['s0-vnf0', 's1-vnf1', 's2-vnf2'], 
                bw=1000, 
                use_htb=True)

    net = topo.startNetwork()
    
    ## network settings ##
    # delete default flows
    net.delFlowsOnSwitches(node_names=list(
        map(lambda x: 's'+str(x), range(n_vnf))))
    # add flows
    net.addFlowsOnSwitch(proto='udp', flows=['client - s0-vnf0-s0-s1-vnf1-s1-s2-vnf2-s2-server', 'server - s2-s1-s0-client'])
    
    # net.addFlowsOnSwitch(proto='udp', flows=[
    #                        'client - ' +
    #                        ''.join(list(map(lambda x: 's'+str(x)+'-vnf' +
    #                                         str(x)+'-s'+str(x)+'-', range(n_vnf))))+'server',
    #                        'server - '+''.join(list(map(lambda x: 's'+str(x)+'-', reversed(range(n_vnf)))))+'client'])
    
    # disable checksum, `node_nameports = ['switch_name:port_name',...]``
    net.disableSwitchCksums(node_nameports=list(
        map(lambda x: 's'+str(x)+':'+'vnf'+str(x), range(n_vnf))))
    net.enterCLI()