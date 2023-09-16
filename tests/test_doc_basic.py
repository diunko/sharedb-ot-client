from sharedb.doc import Doc, Op


# noinspection PyUnresolvedReferences
def test_doc_subscription_basic():
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

    assert d['items', 0, 'bullets'] == ['one', 'two', 'three']
    assert d['items', 1, 'bullets'] == ['four', 'five', 'fix']

    d['items', 0, 'bullets'] = ['testing', 'bla']
    assert d['items', 0, 'bullets'] == ['testing', 'bla']
