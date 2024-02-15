import dataclasses
from dataclasses import dataclass
from typing import Optional

from sharedb import doc
from delta import Delta


class Protocol:
    registry = {}

    @classmethod
    def decode_dict(cls, d: dict):
        action = d['a']
        CLS = cls.registry[action]
        if hasattr(CLS, 'from_dict'):
            return CLS.from_dict(d)
        else:
            d1 = {
                name: d[name] if name in d else f.default
                for name, f in CLS.__dataclass_fields__.items()
                if name in d or not isinstance(f.default, dataclasses._MISSING_TYPE)
            }
            return CLS(**d1)

    @staticmethod
    def encode_dict(m):
        if hasattr(m, 'to_dict'):
            return m.to_dict()
        else:
            return {k: v for k, v in dataclasses.asdict(m).items() if v is not None}

    @classmethod
    def register_message(registry_cls, message_cls):
        action = getattr(message_cls, "a")
        registry_cls.registry[action] = message_cls
        return message_cls


@dataclass
class Snapshot:
    v: int
    data: dict
    type: Optional[str] = "http://sharejs.org/types/JSONv0"


@Protocol.register_message
@dataclass
class Init:
    protocol: int
    protocolMinor: int
    type: str
    id: str

    a = 'init'


@Protocol.register_message
@dataclass
class Handshake:
    id: str

    protocol: int = 1
    protocolMinor: int = 1
    type: Optional[str] = "http://sharejs.org/types/JSONv0"

    a: str = 'hs'


@Protocol.register_message
@dataclass
class Op:
    d: str
    c: str
    src: str
    v: int
    seq: int

    op: list['doc.Op'] = None
    create: Optional[Snapshot] = None

    a: str = 'op'

    @property
    def is_ack(self):
        return self.op is None and self.create is None

    @classmethod
    def from_dict(cls, d: dict):
        d1 = {}
        for name, f in cls.__dataclass_fields__.items():
            if name in d or not isinstance(f.default, dataclasses._MISSING_TYPE):
                d1[name] = d[name] if name in d else f.default
        if 'op' in d:
            # Delta:
            # {"op": {"ops": [{"retain": 15}, {"insert": " "}]}}
            if isinstance(d['op'], dict):
                assert 'ops' in d['op']
                d1['op'] = Delta(ops=d['op']['ops'])

            # Json0:
            # {"op": [{"p": ["improvements", "list"], "oi": []},
            #         {"p": ["chatEvents"], "oi": []}]}
            elif isinstance(d['op'], list):
                d1['op'] = [doc.Op(**op) for op in d['op']]
        return cls(**d1)

    def to_dict(self):
        d = {k: v for k, v in dataclasses.asdict(self).items() if v is not None}

        # Json0
        if isinstance(self.op, list):
            d['op'] = [o.to_dict() for o in self.op]

        # Delta
        elif isinstance(self.op, Delta):
            d['op'] = {'ops': self.op.ops}

        else:
            assert False, f"unknown self.op type, {self.op}"

        return d


@Protocol.register_message
@dataclass
class BulkSub:
    c: str  # collection

    # client subscribes with list of doc_id's
    b: Optional[list[str]] = None

    # server replies with dict[doc_id: Snapshot]
    data: Optional[dict[str, Snapshot]] = None

    a: str = 'bs'


def test_protocol_basic():
    print('====')
    m = Protocol.decode_dict({
        'a': 'init',
        'id': None,
        'protocol': 1,
        'protocolMinor': 1,
        'type': "http://sharejs.org/types/JSONv0"
    })

    print(m)

    m1: Op = Protocol.decode_dict({
        'a': 'op',
        'c': 'collection-a',
        'd': 'document-b',
        'src': 'poij',
        'v': 123,
        'seq': 123,
    })

    print('op, ack', m1, m1.is_ack)

    m = BulkSub(c='coll-id', b=['doc-id-1', 'doc-id-2'])
    print('bulksub', m)
    print('encoded', Protocol.encode_dict(m))


def test_protocol_snapshot():
    print('====')

    m: BulkSub = Protocol.decode_dict({
        'a': 'bs',
        'c': 'collection-a',
        'data': {
            'document-b': {
                'v': 14,
                'data': {'foo': 'qux'}}}})

    print('m1', m)

    assert m.data['document-b'] == {'v': 14, 'data': {'foo': 'qux'}}


def test_protocol_op_embedded():
    print('====')
    m: Op = Protocol.decode_dict({
        'a': 'op',
        'c': 'coll-a',
        'd': 'doc-b',
        'src': 'unk-src-id',
        'v': 123,
        'seq': 1234,
        'op': [{'p': ['a', 'b'], 'oi': 1234}]
    })

    print('decoded', m)
