from sharedb.doc import Doc


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
