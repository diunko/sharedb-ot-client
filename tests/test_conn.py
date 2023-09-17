import asyncio
import random

import pytest
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    force=True)

from sharedb.client_v1 import Connection
from sharedb.doc import Doc, Op

log = logging.getLogger('test_conn')


@pytest.mark.asyncio
async def test_doc_create_and_send_ops():
    log.debug('==== test started ====')
    rand_id = str(random.randint(1000000, 2000000))

    url = 'ws://localhost:17171'

    conn = Connection(url)

    await conn.connect()

    # TODO: what if doc is already there?
    doc = await conn.create_doc(
        doc_id='testing-' + rand_id, coll_id='collection-bla',
        data={
            'qux': 'bla',
            'test': 'foo'
        }
    )

    print('doc')
    print(doc)

    doc.apply([Op(p=['qux'], oi='bla2')])
    doc.apply([Op(p=['qux'], oi='bla3')])
    doc.apply([Op(p=['qux'], oi='bla4')])

    ack_msg = await doc._test_send_one_op_and_wait_ack()
    print('got ack', ack_msg)

    ack_msg = await doc._test_send_one_op_and_wait_ack()
    print('got ack', ack_msg)

    ack_msg = await doc._test_send_one_op_and_wait_ack()
    print('got ack', ack_msg)

    await conn._conn.close()

    assert doc.v == 4
    assert doc.data == {'qux': 'bla4', 'test': 'foo'}


async def connect_and_create_test_doc(data) -> Doc:
    rand_id = str(random.randint(1000000, 2000000))

    url = 'ws://localhost:17171'

    conn = Connection(url)

    await conn.connect()

    # TODO: what if doc is already there?
    doc = await conn.create_doc(
        doc_id='test-doc-' + rand_id, coll_id='test-coll-' + rand_id,
        data=data
    )

    return doc


@pytest.mark.asyncio
async def test_doc_fetch():
    d = await connect_and_create_test_doc({
        'bla': 'qux',
        'test': 'foo'
    })

    await d._conn.close()

    url = 'ws://localhost:17171'
    conn = Connection(url)
    await conn.connect()

    d2 = await conn.fetch_doc(d.id, d.coll_id)
    print(d2)

    d2.apply([Op(p=['qux'], oi='bla2')])
    d2.apply([Op(p=['qux'], oi='bla3')])
    d2.apply([Op(p=['qux'], oi='bla4')])

    ack_msg = await d2._test_send_one_op_and_wait_ack()
    print('got ack', ack_msg)

    ack_msg = await d2._test_send_one_op_and_wait_ack()
    print('got ack', ack_msg)

    ack_msg = await d2._test_send_one_op_and_wait_ack()
    print('got ack', ack_msg)

    await conn.close()


async def connect_and_fetch_doc(doc_id, coll_id) -> Doc:
    url = 'ws://localhost:17171'
    conn = Connection(url)
    await conn.connect()

    doc = await conn.fetch_doc(doc_id, coll_id)
    return doc


@pytest.mark.asyncio
async def test_doc_transform_ops():
    d1 = await connect_and_create_test_doc({
        'bla': 'qux',
        'test': 'foo'
    })
    d1.apply([Op(p=['qux'], oi='bla2')])
    d1.apply([Op(p=['qux'], oi='bla3')])
    d1.apply([Op(p=['qux'], oi='bla4')])

    d2 = await connect_and_fetch_doc(d1.id, d1.coll_id)

    a1 = await d1._test_send_one_op_and_wait_ack()
    print('got ack', a1)
    a1 = await d1._test_send_one_op_and_wait_ack()
    print('got ack', a1)
    a1 = await d1._test_send_one_op_and_wait_ack()
    print('got ack', a1)

    o2 = await d2._conn.recv()
    assert o2['a'] == 'op'
    print('got op on d2')
    o2 = await d2._conn.recv()
    assert o2['a'] == 'op'
    print('got op on d2')
    o2 = await d2._conn.recv()
    assert o2['a'] == 'op'
    print('got op on d2')

    d2.apply([Op(p=['qux'], oi='bla5')])
    a1 = await d2._test_send_one_op_wait_ops_and_ack()

    print('d1', d1)
    print('d2', d2)

    await asyncio.gather(
        d1._conn.close(),
        d2._conn.close())
