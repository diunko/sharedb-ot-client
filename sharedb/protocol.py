import dataclasses
from dataclasses import dataclass
from typing import Optional

from sharedb import doc


class Protocol:
    registry = {}

    @classmethod
    def decode_dict(cls, d: dict):
        action = d['a']
        CLS = cls.registry[action]
        d1 = {
            name: d[name] if name in d else f.default
            for name, f in CLS.__dataclass_fields__.items()
            if name in d or not isinstance(f.default, dataclasses._MISSING_TYPE)
        }
        return CLS(**d1)

    @staticmethod
    def encode_dict(m):
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

    a = 'hs'


@Protocol.register_message
@dataclass
class Op:
    d: str
    c: str
    src: str
    v: int
    seq: int

    op: Optional[list['doc.Op']] = None
    create: Optional[Snapshot] = None

    a = 'op'

    @property
    def is_ack(self):
        return self.op is None and self.create is None


@Protocol.register_message
@dataclass
class BulkSub:
    c: str  # collection

    # client subscribes with list of doc_id's
    b: list[str]

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
