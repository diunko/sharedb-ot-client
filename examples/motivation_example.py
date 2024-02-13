from delta import Delta
from dataclasses import dataclass, field
from typing import Optional, Any, Union
from sharedb.ot.json0 import Json0, Op

Path = list[Union[str, int]]


@dataclass
class Doc:
    data: dict = field(default_factory=dict)
    ops: list[Op] = field(default_factory=list)

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

    def __getattr__(self, item):
        return self.__getitem__(item)


# noinspection PyUnresolvedReferences
async def test_doc_ops():
    d = Doc()

    d['a'] = {'b': {'c': 123}}
    d['a', 'b', 'c'] = 10
    v = d['a', 'b', 'c']

    #######################
    # 1. set some prop
    #    1. to simple value
    #    2. to dict/list
    # 2. get some prop
    #    1. simple value
    #    2. dict/list

    #######################
    # tuple of strings as an accessor is enough?
    # when setting multiple properties
    # keep the reference to some path

    # subscribe to ops from some path
    # e.g.
    d.a.b.c.on('op', lambda op, src: {
        d.cancel(),
        d.start_new(),
        a := d,
        a.skip()
    })

    # how to read input/interactions from the user?
    v = await d.a.b.c.set('x')

    # UI adds an item to a list
    item = await d.a.b.c.append()

    # user clicks a button
    # it changes state of the model
    # e.g. 
    # it increases a counter or sends a signal

    # select item from a menu
    task = process_text(default)
    async for selected_id in d.a.b.c.selected.on('op'):
        await task.cancel()
        task = process_text(texts[selected_id])

    # ======
    d.a.b.c

    print(d.data)
    print(d.ops)

    d.get(['a', 'l']).append('123')

    d.test.something.bla.append(123)


# noinspection PyUnresolvedReferences
async def agent_example():

    d = Doc.create({'chat': []})

    d.chat.append({
        'id': (_id0 := gen_id()),
        'src': 'agent:Help',
        'type': 'system_action',
        'content': 'give me recommendations about this text',
        'functions': llm.definitions.rewrite_suggestions
    })

    messages = get_llm_messages(d.chat)

    async for suggestion in llm.stream_fn_call_items(messages, 'suggestions'):
        assert structure(suggestion, {
            'id': (_id01 := gen_id()),
            'src': 'assistant:Fitzgerald',
            'type': 'suggestion:content',
            'content': 'tell more about pets',
            'question': 'do you like pets?',
            'choices': [
                {'content': 'Yes, I like dogs'},
                {'content': 'Yes, I like cats'},
                {'content': "I'm not a fan of pet animals"}
            ]
        })
        d.chat.append(suggestion)

    reply = await d.chat.on_append(match=lambda op, item: item['reply_to_id'] == _id and op.src == 'user')
    assert reply.structure({
        'id': (_id2 := gen_id()),
        'src': 'user:Jeff',
        'reply_to_id': _id,
        'content': 'Yes, I like dogs'
    })

    messages = d.chat.filter(lambda x: suitable_for_chat(x))
    reply = await llm.reply(messages)

    assert reply.structure({
        'id': gen_id(),
        'reply_to_id': _id2,
        'content': ""
    })


@dataclass
class PathProxy:
    p: list[Union[str, int]] = field(default_factory=list)
    _root: Doc = None
    _ref: Any = None

    def __post_init__(self):
        self._ref = _get_in(self._root.data, self.p)

    def set(self, v):
        _set_in(self._root.data, self.p, v)


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
