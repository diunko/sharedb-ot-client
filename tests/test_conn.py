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
