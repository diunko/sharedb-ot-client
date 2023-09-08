from sharedb.json0 import Op, Json0, clone_op, dict_as_ops
from copy import deepcopy


def test_apply_basic():
    d1 = {'initial': 'something'}

    upd = {
        '5': 'e',
        '6': 'f',
        '7': 'g',
        'next': {
            '1': 'a',
            '2': 'b',
            '3': 'c'
        }
    }

    A = dict_as_ops(upd)
    print('A', A)

    d2 = deepcopy(d1)
    Json0.apply(d2, A)
    print('d', d2)

    assert d2 == {
        'initial': 'something',
        '5': 'e',
        '6': 'f',
        '7': 'g',
        'next': {'1': 'a', '2': 'b', '3': 'c'}}


def test_apply_lists():
    d1 = {
        '5': 'e',
        '6': 'f',
        '7': 'g',
        'next': {
            '1': 'a',
            '2': 'b',
            '3': 'c',
            'L': [0, 1, 2, 3, 4]
        }
    }

    A = [Op(p=['next', 'L', 5], li=5)]
    print('A', A)

    d2 = deepcopy(d1)
    Json0.apply(d2, A)
    print('d', d2)
    assert d2['next']['L'] == [0, 1, 2, 3, 4, 5]

    B = [Op(p=['next', 'L', 3], ld=3)]
    print('B', B)

    Json0.apply(d2, B)
    print('d', d2)
    assert d2['next']['L'] == [0, 1, 2, 4, 5]


def test_transform_basic():
    d1 = {
        'some': {
            'thing': {
                'else': {},
                'other': {'qux': 12}}}}

    # from two sets, left one survives

    d2 = deepcopy(d1)

    # Orig client sends ops_L to Server
    # this is on Orig client and on Server log/doc
    ops_L = [Op(p=['some', 'thing', 'other', 'qux'], oi='left')]
    Json0.apply(d1, ops_L)

    # this is on Other client log/doc
    ops_R = [Op(p=['some', 'thing', 'other', 'qux'], oi='right')]
    Json0.apply(d2, ops_R)

    # Other client sends ops_R to Server
    # now Server transforms what he had so far and gives this to Other client
    ops_L1 = Json0.transform(ops_L, ops_R, 'left')

    # also server transforms Other client's op and sends to Orig client
    ops_R1 = Json0.transform(ops_R, ops_L, 'right')

    # this is what happens on both server and Orig client
    Json0.apply(d1, ops_R1)

    # this is what happens on Other client
    Json0.apply(d2, ops_L1)

    print('======')
    print('d1', d1)
    print('d2', d2)

    assert d1 == d2
    assert d1['some']['thing']['other']['qux'] == 'left'

