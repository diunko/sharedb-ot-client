from delta import Delta
from dataclasses import dataclass, field
from typing import Optional, Any, Union
from sharedb.json0 import Json0, Op

Path = list[Union[str, int]]


# noinspection PyUnresolvedReferences
class OpRef:
    def __init__(self, doc: 'Doc'):
        self._doc = doc
        self._root = doc.data
        self._ref = doc.doc.data
        self._path = []

    def __getattr__(self, item):
        if item == '_':
            pass
        if item == '_ref':
            pass

        self.path.append(item)
        return self

    def match(self, path: Path):
        matched = False
        _ref = self._doc
        indices = []
        for i, (m, p) in enumerate(zip(self._path, path)):
            # m is from matcher
            # p is from op path
            if m == '_':
                indices.append(i)
                # this is a match
            elif m == '_ref':
                _ref = current
                continue
                # go to next component
            elif m == p:
                # this is a match
                matched = True
                break
                # something
        if matched:
            match = (indices, (v0, v1), _ref)
            return match
        else:
            return None

    async def ops_stream(self):
        in_msg = yield -1
        op = None
        while in_msg != -112:
            in_msg = yield op
            op = in_msg

    def notify(self):
        notifier = self.ops_stream()
        self._doc.subscriptions.append(notifier)
        return notifier


# noinspection PyUnresolvedReferences
class Doc:

    def __init__(self):
        self.subscriptions = []

    def _push_op(self, ops: list[Op]):
        # rebase op by the ops waiting to be sent in buffer
        # apply rebased op
        #
        pass

    def on(self):
        return OpRef(self)

    async def ops_match_notify(self, op_ref: OpRef):
        async for op in self._ops():
            if match := op_ref.match(op.p):
                yield match


# noinspection PyUnresolvedReferences
async def test_doc_subscription_basic():
    d = Doc.create({
        'items': [
            {'selected': True,
             'bullets': ['one', 'two', 'three'],
             'text': 'one something two something three something'},
            {'selected': False,
             'bullets': ['four', 'five', 'fix'],
             'text': 'four something five something fix something'},
            {'selected': True,
             'bullets': ['eight', 'six', 'seven'],
             'text': 'eight something six something seven something'},
            {'selected': False,
             'bullets': ['eighteen', 'twenty', 'eleven'],
             'text': 'eighteen something twenty something eleven something'},
        ]})

    changes = [(0, True), (3, True), (1, True), (2, False)]

    for ch in changes:
        i, v = ch
        d._consume_op([Op(**{'p': ['items', i, 'selected'], 'oi': v})])

    idx = 0
    async for (i,), (v1, v0), ref in d.on().items._._ref.selected.notify():
        expected_i, expected_v1 = changes[idx]
        assert i == expected_i
        assert v1 == expected_v1
        assert ref['selected'] == v1
        idx += 1
