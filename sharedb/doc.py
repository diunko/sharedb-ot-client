import asyncio
from dataclasses import dataclass, field
from typing import Optional, Any, Union

from delta import Delta
from sharedb.json0 import Json0, Op

Path = list[Union[str, int]]

DEBUG = False

# noinspection PyUnresolvedReferences
class OpSubscription:
    def __init__(self, doc: 'Doc'):
        self._doc = doc
        self._root = doc.data
        # self._ref = doc.data
        self._path = []
        self._push_q: asyncio.Queue = asyncio.Queue()

    def __getattr__(self, item):
        self._path.append(item)
        return self

    def match(self, path: Path, op: Op):
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
class Doc:
    data: dict = field(default_factory=dict)
    ops: list[Op] = field(default_factory=list)
    subscriptions: list = field(default_factory=list)

    @classmethod
    def create(cls, d: dict):
        doc = Doc(data=d)
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
