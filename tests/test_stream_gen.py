import asyncio
import random


async def stream(q: asyncio.Queue):
    print('channel: start')
    while (op := await q.get()) is not None:
        print('channel: got op', op)
        yield op
        print('channel: after yield')


async def consumer(subscribe):
    print('consumer: start')
    ch, push_q = subscribe()
    print('consumer: got channel')
    i = 0
    async for op in ch:
        print('consumer: (op,i)', (op, i))
        if 3 < i:
            print('consumer: exit condition')
            break
        i += 1
    print('consumer done')


async def socket_recv():
    print('socket: waiting network')
    await asyncio.sleep(1)
    msg = random.randint(1_000_000, 2_000_000)
    print('socket: got message', msg)
    return msg


async def network(channels):
    await asyncio.sleep(1)
    push_q: asyncio.Queue = None
    read_stream, push_q = channels[0]
    for i in range(200, 205):
        msg = await socket_recv()
        print('network: got socket message', msg)
        r = await push_q.put(msg)
        print('network: after pushing message', r)
    await push_q.put(None)


async def main():
    print('main start')
    channels = []

    def subscribe():
        push_q = asyncio.Queue()
        read_stream = stream(push_q)
        channels.append((read_stream, push_q))
        return read_stream, push_q

    net_coro = network(channels)

    # stream reader will consume ops from channel
    # this is called from setting up the listeners
    consumer_coro = consumer(subscribe)

    print('===== gather call below ====')
    # and now, network recv will push ops to channel
    net_r, consume_r = await asyncio.gather(net_coro, consumer_coro)
    print('main done', net_r, consume_r)


asyncio.run(main())
