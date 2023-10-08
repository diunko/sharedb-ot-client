from dataclasses import dataclass, field, asdict, is_dataclass
from typing import List
import pytest

from sharedb.doc import Doc


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
    chat2: Chat = field(default_factory=Chat)


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

    d = Doc[SessionState](DocType=SessionState)
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
