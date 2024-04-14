from typing_extensions import deprecated

import asyncio
import dataclasses
from dataclasses import dataclass, field, asdict, is_dataclass
from typing import Optional, Any, Union, Tuple
from typing import TypeVar, Generic, Type

import random

from sharedb.ot.json0 import Json0, Op
from sharedb.ot.text1 import Text1
from sharedb import client_v1
import sharedb.protocol as proto

from delta import Delta

Path = list[Union[str, int]]

DEBUG = True


@dataclass
class DocOp:
    v: int
    op: Delta

    op_id: str = 'unk-op-id'
    seq: int = 0
    c: str = 'c_default'  # collection
    d: str = 'd_default'  # document id
    src: str = 'unk-src-id'

    def to_dict(self):
        op = {'ops': self.op.ops}
        d = dataclasses.asdict(self)
        d['op'] = op
        return d

    @classmethod
    def from_dict(cls, d: dict):
        d1 = {}
        for name, f in cls.__dataclass_fields__.items():
            if name in d:
                d1[name] = d[name]
            elif not isinstance(f.default, dataclasses._MISSING_TYPE):
                d1[name] = f.default
            else:
                assert False, f"field {name} is missing and has no default value"
        d1['op'] = Delta(ops=d['op']['ops'])
        return cls(**d1)


def test_doc_op_serialize():
    op = DocOp(v=0, op=Delta(ops=[{'insert': 'a'}]))
    d_op = op.to_dict()

    assert d_op == {'v': 0, 'op': {'ops': [{'insert': 'a'}]},
                    'op_id': 'unk-op-id', 'seq': 0, 'c': 'c_default',
                    'd': 'd_default', 'src': 'unk-src-id'}

    op1 = DocOp.from_dict(d_op)
    assert op1 == op

    # deserialize should fail if the non-default field is missing
    d_op1 = {
        # v is missing
        'op': {'ops': [{'insert': 'a'}]}}
    try:
        op1 = DocOp.from_dict(d_op1)
        assert False, f"deserialize unexpectedly succeeded: {op1}"
    except Exception as e:
        assert True, f"deserialize failed (as expected): {e}"


def create_empty_delta():
    return Delta(ops=[{'insert': ''}])


@dataclass
class Doc:
    id: str = 'doc-id'
    coll_id: str = 'coll-id'

    cli_id: str = field(default_factory=lambda: str(random.randint(10 ** 6, 2 * 10 ** 6)))
    seq: int = 0

    v: int = 0
    type: str = 'rich-text'

    data: Delta = field(default_factory=create_empty_delta)
    subscriptions: list = field(default_factory=list)

    pending_ops: list[Delta] = field(default_factory=list)
    _inflight_op: DocOp = None
    _conn: 'client_v1.Connection' = None

    @property
    def full_id(self) -> str:
        return f'{self.coll_id}:{self.id}'

    @classmethod
    def create_(cls, data: Delta, id='doc-id', coll_id='coll-id'):
        doc = Doc(data=data, id=id, coll_id=coll_id, v=0)
        return doc

    def __repr__(self):
        return f'Doc(type={self.type} id={self.id}, coll_id={self.coll_id}, v={self.v}, data={self.data}, _inflight_op={self._inflight_op})'

    @deprecated
    async def create(self, data: dict):
        assert self.v == 0
        assert self.data is None

        self.data = data
        seq, op_id = self._next_seq()
        create_op = {
            'd': self.id,
            'c': self.coll_id,
            'op_id': op_id,
            'seq': seq,
            # 'x': {},
            'v': None,
            'create': {
                'type': 'json0',
                'data': self.data
            }
        }
        self._conn.send(create_op)
        m = await self._conn.cond_recv(matcher=lambda m: (
                m['src'] == self.cli_id
                and m['seq'] == seq
                and m['d'] == self.id
                and m['c'] == self.coll_id))

        assert m['v'] == 0
        self.v += 1

    def apply(self, ops: Delta):
        data1 = Text1.apply(self.data, ops)
        self.data = data1
        self.pending_ops.append(ops)

    def _next_seq(self):
        seq = self.seq
        op_id = f'{self.cli_id}-{str(seq)}'
        self.seq += 1
        return seq, op_id

    def _shift_op_msg(self) -> 'proto.Op':
        assert self._inflight_op is None
        assert 0 < len(self.pending_ops)
        ops0 = self.pending_ops.pop(0)
        seq, op_id = self._next_seq()
        m = proto.Op(
            d=self.id, c=self.coll_id,
            v=self.v, seq=seq,
            src=self._conn.id if self._conn is not None else self.full_id,

            # TODO: fix types arithmetics here
            # for now this might just work
            op=ops0
        )
        self._inflight_op = m
        return m

    # def _shift_op(self) -> DocOp:
    #     assert self._inflight_op is None
    #     assert 0 < len(self.pending_ops)
    #     ops0 = self.pending_ops.pop(0)
    #     seq, op_id = self._next_seq()
    #     d_o = DocOp(v=self.v, op=ops0, seq=seq, op_id=op_id,
    #                 d=self.id, c=self.coll_id)
    #     self._inflight_op = d_o
    #     return d_o

    def _ack_msg(self, m: 'proto.Op'):
        m_inflight: proto.Op = None
        assert (m_inflight := self._inflight_op) is not None
        assert self.v == m.v
        assert m_inflight.seq == m.seq
        if self._conn is not None:
            assert self._conn.id == m.src

        self.v += 1
        self._inflight_op = None

    def _ack(self, op_id, v):
        assert (op := self._inflight_op) is not None
        assert self.v == v
        assert op_id == op.op_id

        self.v += 1

        self._inflight_op = None

    async def sync(self, t=0.2):
        while self._inflight_op is not None:
            await self._test_send_one_op()
            await asyncio.sleep(t)

    async def _test_send_one_op(self):
        assert 0 < len(self.pending_ops)
        m: 'proto.Op' = self._shift_op_msg()
        m.seq = self._conn._next_seq()
        await self._conn._send(m)

    async def _test_send_one_op_and_wait_ack(self):
        assert 0 < len(self.pending_ops)
        m: 'proto.Op' = self._shift_op_msg()
        m.seq = self._conn._next_seq()
        await self._conn._send(m)

        m_ack: proto.Op = await self._conn.recv()
        assert m_ack.is_ack, f'ack expected, got {m_ack}'
        self._ack_msg(m_ack)

        return m_ack

    async def _test_subscribe(self):
        msg0: proto.BulkSub = proto.BulkSub(
            c=self.coll_id,
            b=[self.id]
        )
        await self._conn._send(msg0)

        msg1: proto.BulkSub = await self._conn.recv()
        print('got subscription result msg', msg1)
        assert msg1.a == 'bs'
        assert msg1.c == self.coll_id
        assert self.id in msg1.data
        assert self.v == msg1.data[self.id]['v']

    async def _test_recv_one_op(self):
        msg: proto.Op = await self._conn.recv()
        assert msg.a == 'op'
        assert msg.src != self._conn.id

        print('got op msg from other src', msg)
        return self._push_op_msg(msg)

    async def _test_send_one_op_wait_ops_and_ack(self):
        assert 0 < len(self.pending_ops)
        msg = self._shift_op_msg()
        await self._conn._send(msg)

        msg: proto.Op = None
        while (msg := await self._conn.recv()) and msg.src != self._conn.id:
            print('got msg from other src', msg)
            assert msg.a == 'op', f'should be an op: {msg}'
            self._push_op_msg(msg)

        ack_msg = msg
        assert ack_msg.is_ack

        print('got ack', ack_msg)
        self._ack_msg(ack_msg)

        return ack_msg

    def _push_op1(self, ops: list[Op]):
        pass

    def _push_op_msg(self, op: 'proto.Op') -> 'proto.Op':
        assert op.v == self.v
        # transform all pending ops using transform(pending_op, doc_op, 'L')
        # transform server op using transform(doc_op, pending_op, 'R')

        # rebase in-fight op and buffer ops
        # TODO: extend this to buffer ops as well
        assert 0 == len(self.pending_ops), "only in-flight mode for now"

        DEBUG and print('_push_op_msg', op)
        op_A = op
        if self._inflight_op is not None:
            op_B = self._inflight_op

            ops_A1 = Text1.transform(op_A.op, op_B.op, 'right')
            ops_B1 = Text1.transform(op_B.op, op_A.op, 'left')

            # TODO: XXX inplace!
            op_B.op = ops_B1
            op_B.v = op_A.v + 1

            op_A.op = ops_A1
            # op_A.v += 1

        # apply rebased op
        self.data = Text1.apply(self.data, op_A.op)
        self.v = op_A.v + 1

        for op in op_A.op:
            for sub in self.subscriptions:
                sub(op)

        return op_A

    def _push_op(self, doc_op: DocOp):
        assert doc_op.v == self.v
        # transform all pending ops using transform(pending_op, doc_op, 'L')
        # transform server op using transform(doc_op, pending_op, 'R')

        # rebase in-fight op and buffer ops
        # TODO: extend this to buffer ops as well
        assert 0 == len(self.pending_ops), "only in-flight mode for now"

        op_A = doc_op
        if self._inflight_op is not None:
            op_B = self._inflight_op

            ops_A1 = Json0.transform(op_A.op, op_B.op, 'right')
            ops_B1 = Json0.transform(op_B.op, op_A.op, 'left')

            # TODO: XXX inplace!
            op_B.op = ops_B1
            op_B.v = op_A.v + 1

            op_A.op = ops_A1
            # op_A.v += 1

        # apply rebased op
        Json0.apply(self.data, op_A.op)
        self.v = op_A.v + 1

        for op in op_A.op:
            for sub in self.subscriptions:
                sub(op)

        return op_A

    def Op(self, op: list[Op]) -> 'proto.Op':
        return proto.Op(
            d=self.id,
            c=self.coll_id,
            v=self.v,
            op=op,
            src=self._conn.id if self._conn is not None else 'unk-src-id',
            seq=0
        )
