import asyncio
import dataclasses
from dataclasses import dataclass, field, asdict, is_dataclass
from typing import Optional, Any, Union, Tuple
import random

from delta import Delta
from sharedb.json0 import Json0, Op
from sharedb import client_v1
import sharedb.protocol as proto

Path = list[Union[str, int]]

DEBUG = True

Match = Tuple[Op, Tuple[(Indices := list), (_Ref := Union[list, dict])]]


class OpSubscription:
    def __init__(self, doc: 'Doc'):
        self._doc = doc
        self._root = doc.data
        self._path = []
        self._push_q: asyncio.Queue = asyncio.Queue()

    def __getattr__(self, item):
        self._path.append(item)
        return self

    def match(self, path: Path, op: Op) -> Optional[Match]:
        DEBUG and print('==== mathing p against m')
        DEBUG and print('== m', self._path)
        DEBUG and print('== p', path)

        matched = True
        _ref = self._doc.data
        indices = []
        current = _ref
        i_m, i_p = 0, 0
        while i_m < len(self._path) and i_p < len(path):
            m = self._path[i_m]
            p = path[i_p]
            # m is from matcher
            # p is from op path
            DEBUG and print('i_m, m', i_m, m)
            DEBUG and print('i_p, p', i_p, p)

            if m == '_':
                indices.append(p)
            elif m == '_ref':
                # just store reference to current data node, continue matching
                _ref = current
                i_m += 1
                continue
            elif m != p:
                matched = False
                break
            else:
                assert m == p

            i_m += 1
            i_p += 1
            current = current[p]

        if not matched:
            return None

        return op, (indices, _ref)

    async def read_stream(self):
        DEBUG and print('read_stream: start')
        while (op := await self._push_q.get()) is not None:
            DEBUG and print('read_stream: got op', op)
            yield op

    def notify_op(self, op: Op):
        DEBUG and print('notify_op called', op)
        if m := self.match(op.p, op):
            self._push_q.put_nowait(m)

    def subscribe(self):
        self._doc.subscriptions.append(self.notify_op)
        return self.read_stream()


class OpProxy:
    def __init__(self, doc: 'Doc'):
        self._doc = doc
        self._path = []
        self._ref = self._doc.data

    def __getattr__(self, key):
        if key == '_':
            return self._ref
        v = self._ref[key]
        self._path.append(key)
        if self.is_container(v):
            self._ref = v
            return self
        elif self.is_terminal(v):
            return v
        else:
            assert False, f"Doc[{self._path}] is neither terminal nor container {v}"

    def __getitem__(self, idx):
        return self.__getattr__(idx)

    def __setattr__(self, key, value):
        if key[0] == '_':
            return super().__setattr__(key, value)
        if is_dataclass(value):
            value = asdict(value)
        if isinstance(self._ref, dict):
            # TODO: account for old dict value?
            op = Op(p=[*self._path, key], oi=value)
        elif isinstance(self._ref, list):
            op = Op(p=[*self._path, key], li=value, ld=True)
        else:
            assert False, f"setting attr Doc[{self._path}, {key}] not on a container {self._ref}"
        self._doc.apply([op])

    def __setitem__(self, idx, value):
        if isinstance(self._ref, list):
            if is_dataclass(value):
                value = asdict(value)
            self._ref[idx] = value
            return
        self.__setattr__(idx, value)

    def __delattr__(self, name):
        assert isinstance(self._ref, dict)
        assert name in self._ref
        op = Op(p=[*self._path, name], od=True)
        self._doc.apply([op])

    def __delitem__(self, key):
        if isinstance(self._ref, dict):
            assert key in self._ref
            op = Op(p=[*self._path, key], od=True)
        elif isinstance(self._ref, list):
            assert isinstance(idx := key, int) and idx < len(self._ref)
            op = Op(p=[*self._path, idx], ld=True)
        else:
            assert False, f"{key} should exist in {self._ref}"
        self._doc.apply([op])

    def append(self, item):
        assert isinstance(self._ref, list)
        if is_dataclass(item):
            item = asdict(item)
        L = len(self._ref)
        p = [*self._path, L]
        self._doc.apply([Op(p=p, li=item)])

    @staticmethod
    def is_container(v):
        return isinstance(v, (list, dict))

    @staticmethod
    def is_terminal(v):
        return isinstance(v, (int, str, bool))

@dataclass
class DocOp:
    v: int
    op: list[Op]

    op_id: str = 'unk-op-id'
    seq: int = 0
    c: str = 'c_default'  # collection
    d: str = 'd_default'  # document id
    src: str = 'unk-src-id'

    def to_dict(self):
        return dataclasses.asdict(self)


@dataclass
class Doc:
    id: str = 'doc-id'
    coll_id: str = 'coll-id'

    cli_id: str = field(default_factory=lambda: str(random.randint(10 ** 6, 2 * 10 ** 6)))
    seq: int = 0

    v: int = 0
    data: dict = None
    subscriptions: list = field(default_factory=list)

    pending_ops: list[list[Op]] = field(default_factory=list)
    _inflight_op: DocOp = None
    _conn: 'client_v1.Connection' = None

    Type = Any

    @property
    def full_id(self) -> str:
        return f'{self.coll_id}:{self.id}'

    @classmethod
    def create_(cls, data: dict, id='doc-id', coll_id='coll-id'):
        doc = Doc(data=data, id=id, coll_id=coll_id, v=0)
        return doc

    def __repr__(self):
        return f'Doc(id={self.id}, coll_id={self.coll_id}, v={self.v}, data={self.data}, _inflight_op={self._inflight_op})'

    def __getitem__(self, k):
        if isinstance(k, (list, tuple)):
            path = k
        elif isinstance(k, (int, str)):
            path = [k]
        else:
            assert False, "bad type match"
        return _get_in(self.data, path)

    def __setitem__(self, k, v):
        if isinstance(k, (list, tuple)):
            path = k
        elif isinstance(k, (int, str)):
            path = [k]
        else:
            assert False, "bad type match"
        return _set_in(self.data, path, v)

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

    def apply(self, ops: list[Op]):
        Json0.apply(self.data, ops)
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
            op=ops0
        )
        self._inflight_op = m
        return m

    def _shift_op(self) -> DocOp:
        assert self._inflight_op is None
        assert 0 < len(self.pending_ops)
        ops0 = self.pending_ops.pop(0)
        seq, op_id = self._next_seq()
        d_o = DocOp(v=self.v, op=ops0, seq=seq, op_id=op_id,
                    d=self.id, c=self.coll_id)
        self._inflight_op = d_o
        return d_o

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

    def on(self):
        return OpSubscription(self)

    def Op(self, op: list[Op]) -> 'proto.Op':
        return proto.Op(
            d=self.id,
            c=self.coll_id,
            v=self.v,
            op=op,
            src=self._conn.id if self._conn is not None else 'unk-src-id',
            seq=0
        )

    def op(self) -> Type:
        return OpProxy(self)



def _set_in(ref: dict, path: Path, v: Any):
    k = path[-1]
    for i in range(len(path) - 1):
        p = path[i]
        ref = ref[p]
    ref[k] = v
    return v


def _get_in(ref: dict, path: Path):
    for p in path:
        ref = ref[p]
    return ref
