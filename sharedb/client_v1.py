from asyncio import Future
from dataclasses import dataclass, field
from typing import Callable

import json
import websockets
from websockets.client import WebSocketClientProtocol
import logging

from sharedb import doc

Msg = dict


@dataclass
class Connection:
    url: str

    id: str = None
    seq: int = 0
    docs: dict[str, 'doc.Doc'] = field(default_factory=dict)

    _conn: WebSocketClientProtocol = None
    _matchers: dict[Callable[[Msg], bool], Future] = field(default_factory=dict)

    def __post_init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    async def connect(self):
        assert self._conn is None
        self._conn = await websockets.connect(self.url, user_agent_header='sharedb-py')
        await self._send_dict({'a': 'hs', 'id': None})  # handshake
        m1 = await self.recv()
        assert m1['a'] == 'init'
        # assert m1 == {
        #     "a": "init", "protocol": 1, "protocolMinor": 1,
        #     "id": "54023855a811cde2927615ef6065cc87",
        #     "type": "http://sharejs.org/types/JSONv0"}

        m2 = await self.recv()
        # assert m2 == {
        #     'a': 'hs', 'protocol': 1, 'protocolMinor': 1,
        #     'id': '2937f521a52b4982d104e74823526d35',
        #     'type': 'http://sharejs.org/types/JSONv0'}
        assert m2['a'] == 'hs'  # handshake response
        assert m2['protocol'] == 1
        assert m2['protocolMinor'] == 1
        self.id = m2['id']

    async def _send_dict(self, d: dict):
        data = json.dumps(d)
        self.log.debug('client sent %s message: >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n\t%s',
                       d.get('a', 'action_unknown').upper(), data)
        await self._conn.send(data)

    def cond_recv(self, matcher):
        f = Future()
        self._matchers[matcher] = f
        return f

    async def recv(self):
        try:
            msg_str = await self._conn.recv()
            # self.log.debug('client got raw message: %s', msg_str)
            try:
                m = json.loads(msg_str)
            except Exception:
                self.log.exception('client message decode exception: <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n\t%s',
                                   json.loads(msg_str))
                raise

            self.log.debug('client got message: <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n\t%s',
                           json.loads(msg_str))
            return m

        except Exception as e:
            self.log.warning('<Session %s> recv exception %s', self, e)
            raise

    async def create_doc(self, doc_id, coll_id, data: dict) -> 'doc.Doc':
        # send create
        d = doc.Doc.create_(data=data, id=doc_id, coll_id=coll_id)
        d._conn = self

        self.docs[d.full_id] = d

        msg = {
            'a': 'op',
            'c': d.coll_id, 'd': d.id,
            'v': None,
            'seq': self._next_seq(),
            'x': {},
            'create': {'type': 'json0', 'data': d.data}
        }
        await self._send_dict(msg)

        msg_ack = await self.recv()
        # assert msg_ack == {
        #     "src": "4e4713e6398b8e077a73f416673f7139", "seq": 1, "v": 0,
        #     "a": "op", "c": "examples", "d": "testCreate"}
        assert msg_ack['src'] == self.id
        assert msg_ack['seq'] == msg['seq']
        assert msg_ack['a'] == 'op'

        d.v = msg_ack['v'] + 1

        await d._test_subscribe()

        return d

    async def fetch_doc(self, doc_id, coll_id):
        msg = {
            'a': 'bs',
            'c': coll_id,
            'b': [doc_id]
        }
        await self._send_dict(msg)

        msg_sub = await self.recv()
        # assert msg_sub == {
        #     'a': 'bs', 'c': 'examples',
        #     'data': {
        #         'testCreate': {
        #             'v': 397,
        #             'data': {'bla': 'qux', 'smth': 'foo', 'testing': 123520}}}}
        assert msg_sub['a'] == 'bs'
        assert msg_sub['c'] == coll_id
        assert doc_id in msg_sub['data']

        doc_msg = msg_sub['data'][doc_id]
        d = doc.Doc(
            id=doc_id, coll_id=coll_id, v=doc_msg['v'],
            data=doc_msg['data'],
            _conn=self,
        )
        self.docs[d.full_id] = d
        return d

    def _next_seq(self):
        seq = self.seq
        self.seq += 1
        return seq

    async def close(self):
        assert self._conn is not None
        await self._conn.close()
        self._conn = None
