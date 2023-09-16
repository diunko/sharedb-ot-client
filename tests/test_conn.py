import asyncio

import pytest
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    force=True)

from sharedb.client_v1 import Connection
from sharedb.doc import Doc

log = logging.getLogger('test_conn')


@pytest.mark.asyncio
async def test_doc_create():
    log.debug('==== test started ====')

    url = 'ws://localhost:17171'

    conn = Connection(url)

    await conn.connect()

    doc = await conn.create_doc(
        doc_id='testing', coll_id='collection-bla',
        data={
            'qux': 'bla',
            'test': 'foo'
        }
    )

    print('doc')
    print(doc)

    await conn._conn.close()
