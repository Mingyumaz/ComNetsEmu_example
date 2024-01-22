# SimpleCoin Workflow
## Coin_test Debug
Base on `simplecoin.py` comment，copy example program to coin_test.py
### Start Debug
- start Comnetsemu

```bash
vagrant up testbed
vagrant ssh testbed
cd \vagrant\emulator\
sudo python3 topo.py
```

- run `client.py` in client shell, `server.py` in server shell.
- in vnf1 shell run `python3 -m pdb ./simpleemu/coin_test.py`

- add breakpoints
```pdb
(Pdb) b 10
Breakpoint 1 at /volume/simpleemu/coin_test.py:10
(Pdb) b 14
*** Blank or comment
(Pdb) b 26
Breakpoint 2 at /volume/simpleemu/coin_test.py:26
(Pdb) b 36
Breakpoint 3 at /volume/simpleemu/coin_test.py:36
```

### Analyse
first go to init fuction of SimpleCOIN
`def __init__(self, ifce_name: str, mtu: int = 1500, chunk_gap: float = 0.0015`
`main` and `func` use partial func to called by `app.main()` and `app.func()`

`id`: function for each id store in `self.func_map` with `self.func_map[id] = func`.
`pid`: index of process, in `submit_func` store all of function, put the func into this `pid` process's queue.

in `function_loop` get the Queue for this process, from the Queue get the id, and run.

breakpoints 2,3 don't break while debug, before app.run(), `main` and `func` partial in `app.main` and `app.func`.


