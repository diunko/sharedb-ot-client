import logging
import random

import asyncio
import pytest

from sharedb.client_v1 import Connection
from sharedb.doc import Doc
from delta import Delta

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    force=True)
log = logging.getLogger('test_conn')


@pytest.mark.asyncio
async def test_doc_create_and_send_ops():
    log.debug('==== test started ====')
    rand_id = str(random.randint(1000000, 2000000))

    url = 'ws://localhost:17171'

    conn = Connection(url)

    await conn.connect()

    # TODO: what if doc is already there?
    doc = await conn.create_text(
        doc_id='testing-' + rand_id, coll_id='collection-bla',
        data=Delta(ops=[{'insert': 'this is a story\n'}])
    )

    print('doc')
    print(doc)

    doc.apply(Delta(ops=[{'retain': 4}, {'insert': ' truly'}]))

    print('doc changed')
    print(doc)

    if True:
        ack_msg = await doc._test_send_one_op_and_wait_ack()
        print('got ack', ack_msg)

    await conn._conn.close()

    assert doc.v == 2
    assert doc.data == Delta(ops=[{'insert': 'this truly is a story\n'}])


# TODO: adapt to rich-text type
async def connect_and_create_test_doc(data) -> Doc:
    rand_id = str(random.randint(1000000, 2000000))

    url = 'ws://localhost:17171'

    conn = Connection(url)

    await conn.connect()

    # TODO: what if doc is already there?
    doc = await conn.create_text(
        doc_id='test-doc-' + rand_id, coll_id='test-coll-' + rand_id,
        data=data
    )

    return doc


@pytest.mark.asyncio
async def test_doc_fetch():
    d = await connect_and_create_test_doc(
        Delta(ops=[{'insert': 'testing testing testing\n'}])
    )

    await d._conn.close()

    url = 'ws://localhost:17171'
    conn = Connection(url)
    await conn.connect()

    d2 = await conn.fetch_text(d.id, d.coll_id)
    print(d2)

    d2.apply(Delta(ops=[{'insert': 'testing '}]))

    ack_msg = await d2._test_send_one_op_and_wait_ack()
    print('got ack', ack_msg)

    await conn.close()


async def connect_and_fetch_doc(doc_id, coll_id) -> Doc:
    url = 'ws://localhost:17171'
    conn = Connection(url)
    await conn.connect()

    doc = await conn.fetch_text(doc_id, coll_id)
    return doc


@pytest.mark.asyncio
async def test_doc_create():
    d1 = await connect_and_create_test_doc(
        Delta(ops=[{'insert': 'testing\n'}])
    )
    print('d1', d1)

    await d1._conn.close()


@pytest.mark.asyncio
async def test_doc_transform_ops():
    d1 = await connect_and_create_test_doc(
        Delta(ops=[{'insert': 'testing\n'}])
    )
    d1.apply(Delta(ops=[{'retain': 7}, {'insert': ' something'}]))

    d2 = await connect_and_fetch_doc(d1.id, d1.coll_id)

    a1 = await d1._test_send_one_op_and_wait_ack()
    print('got ack', a1)

    o2 = await d2._conn.recv_dict()
    assert o2['a'] == 'op'
    print('got op on d2')

    d2.apply(Delta(ops=[{'retain': 16}, {'insert': 'else'}]))
    a1 = await d2._test_send_one_op_wait_ops_and_ack()

    print('d2 op sent')

    o_d1_2 = await d1._test_recv_one_op()

    print('o_d1_2', o_d1_2)
    print('d1', d1)
    print('d2', d2)

    await asyncio.gather(
        d1._conn.close(),
        d2._conn.close())


@pytest.mark.asyncio
async def test_conn_two_docs_sync():
    d1 = await connect_and_create_test_doc(
        Delta(ops=[{'insert': 'testing\n'}])
    )
    d1.apply(Delta(ops=[{'retain': 7}, {'insert': ' something'}]))

    d2 = await connect_and_fetch_doc(d1.id, d1.coll_id)
    d2._conn.start_updates()

    try:
        a1 = await d1._test_send_one_op_and_wait_ack()
        print('got ack', a1)

        # connection handles incoming ops for d2
        await asyncio.sleep(0.5)

        print('doc d2 after waiting\n\t', d2)
        assert d2.data == Delta(ops=[{'insert': 'testing something\n'}])

    finally:
        await asyncio.gather(
            d1._conn.close(),
            d2._conn.close())
