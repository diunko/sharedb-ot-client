import asyncio

import pytest

from sharedb.doc import Doc, Op


@pytest.mark.asyncio
async def test_doc_subscription_basic():
    d = Doc.create_({
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

    changes = [(0, False), (3, True), (1, True), (2, {'a': 'b'})]

    async def subscribe():
        idx = 0
        async for op, ((i, *_), ref) in d.on().items._._ref.selected.subscribe():
            print('got notification on op', op)
            expected_i, expected_v1 = changes[idx]
            assert i == expected_i
            assert ref['selected'] == expected_v1
            idx += 1
            if idx == len(changes):
                break

    async def receive_ops():
        await asyncio.sleep(0.1)
        for ch in changes:
            i, v = ch
            d._push_op(d.Op([Op(**{'p': ['items', i, 'selected'], 'oi': v})]))

        assert d['items', 0, 'selected'] == False

    await asyncio.gather(subscribe(), receive_ops())


@pytest.mark.skip
def test_update():
    d = Doc.create_({
        'profile': {
            'ava': 'blabla.jpg',
            'nickname': 'ququ',
        },
        'items': [
            {'id': 123,
             'selected': True,
             'content': 'oijaoijfdoiajdf'},
            {'id': 123,
             'selected': True,
             'content': 'oijaoijfdoiajdf'},
            {'id': 123,
             'selected': True,
             'content': 'oijaoijfdoiajdf'},
            {'id': 123,
             'selected': True,
             'content': 'oijaoijfdoiajdf'},
        ]
    })

    d.items[2].selected = False

    d.profile.ava = 'ququ.jpg'
    d._push_op(d.Op([Op(p=['profile', 'ava'], oi='ququ.jpg')]))
