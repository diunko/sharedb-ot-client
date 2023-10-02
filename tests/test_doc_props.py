from dataclasses import dataclass, field, asdict, is_dataclass
from typing import List
import pytest

from sharedb.doc import Doc as BaseDoc, Op


class OpProxy:
    def __init__(self, doc: BaseDoc):
        self._doc = doc
        self._path = []
        self._ref = self._doc.data

    def __getattr__(self, key):
        if key == '_':
            return self._ref
        self._path.append(key)
        v = self._ref[key]
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
class Message:
    id: str = None
    role: str = 'assistant'
    content: list[str] = field(default_factory=list)


@dataclass
class Chat:
    messages: List[Message] = field(default_factory=list)
    is_loaded: bool = True


@dataclass
class SessionState:
    chat: Chat = field(default_factory=Chat)


@dataclass
class SessionStateDoc(BaseDoc):
    Type = SessionState

    def __post_init__(self):
        self.data = asdict(self.Type())

    def op(self) -> Type:
        return OpProxy(self)


@pytest.mark.skip
def test_doc_props_typehints_exmample1():
    print('====')

    c = SessionState()
    c.chat.messages.append(Message(
        id='msg-id-123',
        role='user',
        content=['hi there! how can I help?']
    ))

    c.chat.messages[0].content.append(' and also one question: do I talk a lot?')

    print(asdict(c))


# @pytest.mark.skip
def test_doc_props_typehints_exmample2():
    print('====')

    d = SessionStateDoc()
    print('doc v0', d)

    ########
    # dict container

    # set and get simple property in a dict container
    assert d.op().chat.is_loaded
    d.op().chat.is_loaded = False
    assert not d.op().chat.is_loaded

    # set and get a container property in a dict container
    d.op().chat = Chat(messages=[Message(id='m-0', role='user', content=['testing', ' bla'])])
    # assert d.op().chat | dict == asdict(Chat(messages=[Message(id='123', role='user', content=['testing', ' bla'])]))
    assert d.op().chat._ == asdict(Chat(messages=[Message(id='m-0', role='user', content=['testing', ' bla'])]))

    ########
    # list container

    # append to the end of the list
    d.op().chat.messages.append(Message(id='m-1', role='user', content=['testing', ' 123']))
    d.op().chat.messages.append(Message(id='m-2', role='user', content=['testing', ' 234']))
    assert d.op().chat.messages[2]._ == asdict(Message(id='m-2', role='user', content=['testing', ' 234']))

    # set and get list item
    d.op().chat.messages[1] = Message(id='m-1.1', role='system', content=['bla', ' testing'])
    assert d.op().chat.messages[1]._ == asdict(Message(id='m-1.1', role='system', content=['bla', ' testing']))

    # delete list item
    m2 = d.op().chat.messages[2]._
    del d.op().chat.messages[1]
    assert d.op().chat.messages[1]._ == m2

    # delete dict item
    del d.op().chat.messages[1].role
    assert d.op().chat.messages[1]._ == {'id': 'm-2', 'content': ['testing', ' 234']}

    print('doc v1', d)
