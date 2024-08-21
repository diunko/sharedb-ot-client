import asyncio
import random

import pytest
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    force=True)

from sharedb.client_v1 import Connection
from sharedb.doc import Doc, Op
from sharedb.utils import aclosing

log = logging.getLogger('test_conn')


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


async def connect_and_fetch_doc(doc_id, coll_id) -> Doc:
    url = 'ws://localhost:17171'
    conn = Connection(url)
    await conn.connect()

    doc = await conn.fetch_doc(doc_id, coll_id)
    return doc


@pytest.mark.asyncio
async def test_doc_sync_one_op():
    d1 = await connect_and_create_test_doc({
        'bla': 'qux',
        'qux': 'bla1'
    })

    d2 = await connect_and_fetch_doc(d1.id, d1.coll_id)

    d1._conn.start_updates()
    d2._conn.start_updates()

    async with aclosing(d1._conn), aclosing(d2._conn):
        d1.apply([Op(p=['qux'], oi='bla2')])
        await d1.sync()

        await asyncio.sleep(1)
        assert d2.data == {
            'bla': 'qux',
            'qux': 'bla2'
        }


@pytest.mark.asyncio
async def test_doc_sync_two_ops():
    d1 = await connect_and_create_test_doc({
        'bla': 'qux',
        'qux': 'bla1'
    })

    d2 = await connect_and_fetch_doc(d1.id, d1.coll_id)

    d1._conn.start_updates()
    d2._conn.start_updates()

    async with aclosing(d1._conn), aclosing(d2._conn):
        d1.apply([Op(p=['qux'], oi='bla2')])
        d1.apply([Op(p=['qux2'], oi='bla3')])
        await d1.sync()

        await asyncio.sleep(1)
        assert d2.data == {
            'bla': 'qux',
            'qux': 'bla2',
            'qux2': 'bla3'
        }


@pytest.mark.asyncio
async def test_doc_sync_concurrent_ops():
    d1 = await connect_and_create_test_doc({
        'bla': 'qux',
        'qux': 'bla1'
    })

    d2 = await connect_and_fetch_doc(d1.id, d1.coll_id)

    d1._conn.start_updates()
    d2._conn.start_updates()

    async with aclosing(d1._conn), aclosing(d2._conn):
        d1.apply([Op(p=['qux'], oi='bla2')])
        d1.apply([Op(p=['qux2'], oi='bla3')])

        d2.apply([Op(p=['bla'], oi='qux2')])
        await d2.sync()
        await asyncio.sleep(1)

        await d1.sync()

        await asyncio.sleep(1)

        assert d2.data == {
            'bla': 'qux2',
            'qux': 'bla2',
            'qux2': 'bla3'
        }

        assert d1.data == {
            'bla': 'qux2',
            'qux': 'bla2',
            'qux2': 'bla3'
        }
