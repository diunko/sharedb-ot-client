import asyncio
import dataclasses
from dataclasses import dataclass, field
from typing import Optional, Any, Union, Tuple
import random

from delta import Delta
from sharedb.json0 import Json0, Op
from sharedb import client_v1

Path = list[Union[str, int]]

DEBUG = False

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


@dataclass
class DocOp:
    v: int
    op: list[Op]

    op_id: str = 'unk-op-id'
    seq: int = 0
    c: str = 'c_default'  # collection
    d: str = 'd_default'  # document id

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

    @property
    def full_id(self) -> str:
        return f'{self.coll_id}:{self.id}'

    @classmethod
    def create_(cls, data: dict, id='doc-id', coll_id='coll-id'):
        doc = Doc(data=data, id=id, coll_id=coll_id, v=0)
        return doc

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

    def _shift_op(self) -> DocOp:
        assert self._inflight_op is None
        assert 0 < len(self.pending_ops)
        ops0 = self.pending_ops.pop(0)
        seq, op_id = self._next_seq()
        d_o = DocOp(v=self.v, op=ops0, seq=seq, op_id=op_id,
                    d=self.id, c=self.coll_id)
        self._inflight_op = d_o
        return d_o

    def _ack(self, op_id, v):
        assert (op := self._inflight_op) is not None
        assert self.v == v
        assert op_id == op.op_id

        self.v += 1

        self._inflight_op = None

    async def _test_send_one_op_and_wait_ack(self):
        assert 0 < len(self.pending_ops)
        doc_op = self._shift_op()
        msg = {
            'a': 'op', 'd': self.id, 'c': self.coll_id,
            'v': self.v,
            'seq': self._conn._next_seq(),
            'x': {},
            'op': [o.to_dict() for o in doc_op.op]
        }
        await self._conn._send_dict(msg)

        ack_msg = await self._conn.recv()
        self._ack(doc_op.op_id, ack_msg['v'])

        return ack_msg

    def _push_op(self, ops: list[Op]):
        # rebase op by the ops waiting to be sent in buffer

        # apply rebased op
        Json0.apply(self.data, ops)

        for op in ops:
            for sub in self.subscriptions:
                sub(op)

    def on(self):
        return OpSubscription(self)


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
