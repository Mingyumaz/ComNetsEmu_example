import time
from simplecoin import SimpleCOIN
from simpleudp import simpleudp

# network interface: 'vnf1-s1'
# device ip: '10.0.0.13'

n_submit = 0

app = SimpleCOIN(ifce_name='vnf1-s1',n_func_process=2)

@app.main()
def main(simplecoin, af_packet):
    # parse the raw packet to get the ip/udp infomations like ip, port, protocol, data
    simplecoin.submit_func(pid=0,id='submit_count',args=('pid=0 @ main',))
    time.sleep(1)
    print('*** sleep 1s')
    simplecoin.submit_func(pid=1,id='submit_count',args=('pid=1 @ main',))
    time.sleep(1)
    print('*** sleep 1s')
    simplecoin.submit_func(pid=0,id='submit_count',args=('pid=0 @ main',))


@app.func('submit_count')
def submit_count(simplecoin, myvalue):
    global n_submit
    n_submit += 1
    print(myvalue, n_submit)
    if n_submit == 1:
        print('before submit in func')
        simplecoin.submit_func(pid=-1,id='submit_count',args=('pid=-1 @ func',))
        print('after submit in func')


if __name__ == "__main__":
    app.run()

