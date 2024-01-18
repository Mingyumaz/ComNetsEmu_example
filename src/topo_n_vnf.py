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


    topo.addHostNodes(node_names=['client', 'server'],
                        ip_prefix='10.0.0.', ip_suffixes=['10', '30'],
                        dimage='simple_dev:1.0', volume=None,
                        docker_args={"cpuset_cpus": '0', 'cpu_quota': 30000})
    for i in range(n_vnf):
        topo.addHostNodes(node_names=['vnf'+ str(i)],
                            ip_prefix='10.0.0.', ip_suffixes=[str(i+11)],
                            dimage='simple_dev:1.0', volume=None,
                            docker_args={"cpuset_cpus": str(i//3+1), 'cpu_quota': 30000})


    topo.addSwitchNodes(node_names=list(
        map(lambda x: 's'+str(x), range(n_vnf))))
    
    # create links, `bw` is bandwith, unit of bandwith is 'Mbit/s'
    topo.addLinks(links=['client - '+''.join(list(map(lambda x: 's'+str(x)+'-', range(n_vnf))))+'server'] +
                    list(map(lambda x: 's'+str(x)+'-'+'vnf'+str(x), range(n_vnf))), bw=1000, delay='10ms', use_htb=True)
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