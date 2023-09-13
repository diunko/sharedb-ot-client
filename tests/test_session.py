import asyncio
from sharedb.client_v0 import ClientSession
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s')


async def main():
    c = ClientSession()
    await c.connect('ws://localhost:17171')

    await c.send_dict({'a': 'hs', 'id': None})
    m = await c.recv()
    m = await c.recv()
    await c.send_dict({"a": "bs", "c": "examples",
                       "b": ["main", "chat"]})
    m = await c.recv()
    assert m['a'] == 'bs'
    print(m['data']['chat'])
    # {'v': 2, 'data':
    #   {'documentInfo': {'evaluations': 0, 'reset': 0,
    #                     'loading': False, 'evaluation': {}},
    #    'improvements': [],
    #    'testing': 123123}}

    print(m['data']['main'])
    # {'v': 2, 'data': {'ops': [{'insert': 'testing\n'}]},
    #  'type': 'http://sharejs.org/types/rich-text/v1'}

    cur_version = 1
    seq = 0

    while True:
        while 0 < len(c.conn.messages):
            m = await c.recv()
            print('incoming message', m)
            # if m['a'] == 'op' and m['c'] == 'examples' and m['d'] == 'chat':
            #     cur_version = m['v']
        await c.send_dict({"a": "op", "c": "examples", "d": "chat",
                           "v": cur_version,
                           "seq": seq,
                           "op": [{"p": ["testing"], "na": 2}]})
        seq += 1
        await asyncio.sleep(0.1)
        while 0 < len(c.conn.messages):
            m = await c.recv()
            print('incoming message', m)
        await asyncio.sleep(0.1)
        while 0 < len(c.conn.messages):
            m = await c.recv()
            print('incoming message', m)
        await asyncio.sleep(0.1)
        while 0 < len(c.conn.messages):
            m = await c.recv()
            print('incoming message', m)
        await asyncio.sleep(0.1)
        while 0 < len(c.conn.messages):
            m = await c.recv()
            print('incoming message', m)
        await asyncio.sleep(0.1)
        while 0 < len(c.conn.messages):
            m = await c.recv()
            print('incoming message', m)

        await asyncio.sleep(5)

    async for m in c.recv_while(fn=lambda: True):
        print('m', m)

    c.send_dict({})
    m = await c.recv()
    m = await c.recv()
    m = await c.recv()
    m = await c.recv()
    m = await c.recv()


asyncio.run(main(), debug=True)
