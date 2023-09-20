from dataclasses import dataclass
from typing import Optional

import doc


@dataclass
class Snapshot:
    v: int
    data: dict
    type: Optional[str] = "http://sharejs.org/types/JSONv0"


# server messages

@dataclass
class Init:
    protocol: int
    protocolMinor: int
    type: str
    id: str

    a = 'init'


@dataclass
class Handshake:
    id: str

    protocol: int = 1
    protocolMinor: int = 1
    type: Optional[str] = "http://sharejs.org/types/JSONv0"

    a = 'hs'


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


@dataclass
class BulkSub:
    c: str  # collection

    # client subscribes with list of doc_id's
    b: list[str]

    # server replies with dict[doc_id: Snapshot]
    data: Optional[dict[str, Snapshot]] = None

    a = 'bs'
