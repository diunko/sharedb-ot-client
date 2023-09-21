import asyncio
from sharedb.client_v1 import Connection
from sharedb.doc import Doc, Op
import logging
import json
import random

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s')


async def connect_and_fetch_doc(url, doc_id, coll_id) -> Doc:
    conn = Connection(url)
    await conn.connect()

    doc = await conn.fetch_doc(doc_id, coll_id)
    return doc


def print_chat_doc(doc):
    repr = {k: v for k, v in doc.data.items() if k != 'logs'}
    print(json.dumps(repr, indent=2))


async def main():
    doc = await connect_and_fetch_doc(
        "ws://localhost:8080",
        "chat",
        "9561449331278304")

    print('==== fetched the doc! ====')
    print_chat_doc(doc)

    doc.apply([Op(
        p=['improvements', 'list', 0],
        li={
            "improvement": "this comes from python client!",
            "category": "my very own",
            "key": str(random.randint(1000000, 2000000))
        }
    )])

    ack_msg = await doc._test_send_one_op_and_wait_ack()
    print('got ack', ack_msg)

    await asyncio.sleep(1)
    await doc._conn.close()


asyncio.run(main(), debug=True)
