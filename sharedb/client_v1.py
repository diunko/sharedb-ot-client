from asyncio import Future, create_task
from dataclasses import dataclass, field
from typing import Callable, List
from collections import defaultdict

import json
import websockets
from websockets.client import WebSocketClientProtocol
import logging
from loguru import logger

from sharedb import doc, text
import sharedb.protocol as proto
from delta import Delta

Msg = dict


@dataclass
class Connection:
    url: str

    id: str = None
    seq: int = 0
    docs: dict[str, 'doc.Doc'] = field(default_factory=dict)
    collections: dict[str, dict[str, 'doc.Doc']] = field(default_factory=lambda: defaultdict(dict))

    _conn: WebSocketClientProtocol = None
    _matchers: dict[Callable[[Msg], bool], Future] = field(default_factory=dict)
    _stop = False
    _main_ops_loop_coro = None
    _main_ops_loop_task = None

    def __post_init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    async def connect(self):
        assert self._conn is None
        self._conn = await websockets.connect(self.url, user_agent_header='sharedb-py')
        await self._send_dict({'a': 'hs', 'id': None})  # handshake
        m1 = await self.recv_dict()
        assert m1['a'] == 'init'
        # assert m1 == {
        #     "a": "init", "protocol": 1, "protocolMinor": 1,
        #     "id": "54023855a811cde2927615ef6065cc87",
        #     "type": "http://sharejs.org/types/JSONv0"}

        m2 = await self.recv_dict()
        # assert m2 == {
        #     'a': 'hs', 'protocol': 1, 'protocolMinor': 1,
        #     'id': '2937f521a52b4982d104e74823526d35',
        #     'type': 'http://sharejs.org/types/JSONv0'}
        assert m2['a'] == 'hs'  # handshake response
        assert m2['protocol'] == 1
        assert m2['protocolMinor'] == 1
        self.id = m2['id']

    def start_updates(self):
        assert self._main_ops_loop_coro is None
        self._main_ops_loop_coro = self.main_ops_loop()
        self._main_ops_loop_task = create_task(self._main_ops_loop_coro)

    @logger.catch
    async def main_ops_loop(self):
        try:
            while not self._stop:
                m: proto.Op = await self.recv()
                self.log.debug('main_ops_loop: got msg: %s', m)
                assert m.a == 'op', f'expecting only an Op msg, got: {m}'
                d = self.collections[m.c][m.d]
                if m.is_ack:
                    d._ack_msg(m)
                else:
                    d._push_op_msg(m)
        except websockets.exceptions.ConnectionClosedOK:
            self._stop = True
        except Exception as e:
            self.log.exception('main_ops_loop: uncaught exception')
            raise e

    async def _send(self, m):
        d = proto.Protocol.encode_dict(m)
        await self._send_dict(d)

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
                m_dict = json.loads(msg_str)
                m = proto.Protocol.decode_dict(m_dict)
            except Exception:
                self.log.exception('client message decode exception: <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n\t%s',
                                   json.loads(msg_str))
                raise

            self.log.debug('client got %s message: <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n\t%s', m.a, m)
            return m

        except Exception as e:
            self.log.warning('<Session %s> recv exception %s', self, e)
            raise

    async def recv_dict(self):
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

    async def create_text(self, doc_id, coll_id, data: Delta) -> 'text.Doc':
        d = text.Doc.create_(data=data, id=doc_id, coll_id=coll_id)
        d._conn = self

        self.docs[d.full_id] = d
        self.collections[d.coll_id][d.id] = d

        msg = {
            'a': 'op',
            'c': d.coll_id, 'd': d.id,
            'v': None,
            'seq': self._next_seq(),
            'x': {},
            'create': {
                'type': 'rich-text',

                # TODO: check it out. Looks like this should be a list of delta's ops
                # TODO: should I clone it? likely yes.
                'data': d.data.ops
            }
        }
        await self._send_dict(msg)

        msg_ack = await self.recv_dict()
        # assert msg_ack == {
        #     "src": "4e4713e6398b8e077a73f416673f7139", "seq": 1, "v": 0,
        #     "a": "op", "c": "examples", "d": "testCreate"}
        assert msg_ack['src'] == self.id
        assert msg_ack['seq'] == msg['seq']
        assert msg_ack['a'] == 'op'

        d.v = msg_ack['v'] + 1

        await d._test_subscribe()

        return d

    async def create_doc(self, doc_id, coll_id, data: dict) -> 'doc.Doc':
        # send create
        d = doc.Doc.create_(data=data, id=doc_id, coll_id=coll_id)
        d._conn = self

        self.docs[d.full_id] = d
        self.collections[d.coll_id][d.id] = d

        msg = {
            'a': 'op',
            'c': d.coll_id, 'd': d.id,
            'v': None,
            'seq': self._next_seq(),
            'x': {},
            'create': {'type': 'json0', 'data': d.data}
        }
        await self._send_dict(msg)

        msg_ack = await self.recv_dict()
        # assert msg_ack == {
        #     "src": "4e4713e6398b8e077a73f416673f7139", "seq": 1, "v": 0,
        #     "a": "op", "c": "examples", "d": "testCreate"}
        assert msg_ack['src'] == self.id
        assert msg_ack['seq'] == msg['seq']
        assert msg_ack['a'] == 'op'

        d.v = msg_ack['v'] + 1

        await d._test_subscribe()

        return d

    async def fetch_many(self, doc_ids: List[str], coll_id):

        msg = {
            'a': 'bs',
            'c': coll_id,
            'b': doc_ids
        }
        await self._send_dict(msg)

        msg_sub = await self.recv_dict()
        assert msg_sub == {
            "data": {"mainQuillDoc": {"v": 1, "data": {"ops": []},
                                      "type": "http://sharejs.org/types/rich-text/v1"},
                     "playgroundQuillDoc": {"v": 1, "data": {"ops": []},
                                            "type": "http://sharejs.org/types/rich-text/v1"},
                     "stateDoc": {"v": 1, "data": {
                         "documentInfo": {"isEvaluating": False, "isImproving": False, "isFixing": False,
                                          "isReplying": False, "guideline": False, "evaluation": {},
                                          "settings": {"isColoringEnabled": True, "isStreamingEnabled": True}},
                         "improvements": {"list": [], "isLoading": False}, "chatEvents": [], "logs": [],
                         "feedbacks": [],
                         "localSettings": {}}}},
            "a": "bs", "c": "170775850673012"}

        assert msg_sub['a'] == 'bs'
        assert msg_sub['c'] == coll_id
        for _id in doc_ids:
            assert _id in msg_sub['data']

        docs = {}
        for _id in doc_ids:
            doc_msg = msg_sub['data'][_id]
            doc_type = msg_sub['data'][_id].get('type', 'json0')
            d = doc.Doc(
                id=_id, coll_id=coll_id, v=doc_msg['v'],
                data=doc_msg['data'],
                _conn=self,
            )
        self.docs[d.full_id] = d
        self.collections[d.coll_id][d.id] = d
        return d

    async def fetch_text(self, doc_id, coll_id):
        msg = {
            'a': 'bs',
            'c': coll_id,
            'b': [doc_id]
        }
        await self._send_dict(msg)

        msg_sub = await self.recv_dict()
        # assert msg_sub == {
        #     'a': 'bs',
        #     'c': 'test-coll-1060088',
        #     'data': {
        #         'test-doc-1060088': {
        #             'v': 1,
        #             'data': {'ops': [{'insert': 'testing testing testing\n'}]},
        #             'type': 'http://sharejs.org/types/rich-text/v1'}}}

        assert msg_sub['a'] == 'bs'
        assert msg_sub['c'] == coll_id
        assert doc_id in msg_sub['data']

        doc_msg = msg_sub['data'][doc_id]
        d = text.Doc(
            id=doc_id, coll_id=coll_id, v=doc_msg['v'],
            data=Delta(ops=doc_msg['data']['ops']),
            _conn=self,
        )
        self.docs[d.full_id] = d
        self.collections[d.coll_id][d.id] = d
        return d

    async def fetch_doc(self, doc_id, coll_id):
        msg = {
            'a': 'bs',
            'c': coll_id,
            'b': [doc_id]
        }
        await self._send_dict(msg)

        msg_sub = await self.recv_dict()
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
        self.collections[d.coll_id][d.id] = d
        return d

    def _next_seq(self):
        seq = self.seq
        self.seq += 1
        return seq

    async def close(self):
        assert self._conn is not None
        await self._conn.close()
        self._stop = True
        if self._main_ops_loop_task is not None:
            await self._main_ops_loop_task
            self._main_ops_loop_task = None
        self._conn = None

    async def aclose(self):
        await self.close()


def test_conn_collections_init():
    c = Connection('testurl')
    c.collections['coll-a']['bla'] = doc.Doc(id='testingdoc')

    print(c.collections)
