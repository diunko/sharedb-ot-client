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
async def test_doc_create():
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

    ack_msg = await doc._send_one_op_and_wait_ack()
    print('got ack', ack_msg)

    ack_msg = await doc._send_one_op_and_wait_ack()
    print('got ack', ack_msg)

    ack_msg = await doc._send_one_op_and_wait_ack()
    print('got ack', ack_msg)

    await conn._conn.close()

    assert doc.v == 4
    assert doc.data == {'qux': 'bla4', 'test': 'foo'}
