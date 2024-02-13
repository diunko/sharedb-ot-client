from sharedb.ot.json0 import Op, Json0


def test_json0_list_op__same_list__reset_other():
    print('====')
    d0 = {'a': {'b': [10, 11, 12, 13, 14]}}

    ################
    # new op inserts after applied
    o_a = [Op(p=['a', 'b', 3], li=23, ld=13)]
    o_n = [Op(p=['a', 'b', 4], li=24)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 4], li=24)]
    assert o_n1_r == [Op(p=['a', 'b', 4], li=24)]

    ################
    # new op inserts before applied
    o_a = [Op(p=['a', 'b', 3], li=23, ld=13)]
    o_n = [Op(p=['a', 'b', 2], li=22)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 2], li=22)]
    assert o_n1_r == [Op(p=['a', 'b', 2], li=22)]

    ################
    # new op inserts at the same place as applied
    o_a = [Op(p=['a', 'b', 3], li=23, ld=13)]
    o_n = [Op(p=['a', 'b', 3], li=33)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 3], li=33)]
    assert o_n1_r == [Op(p=['a', 'b', 3], li=33)]

    ################
    # new op deletes at the same place as applied
    o_a = [Op(p=['a', 'b', 3], li=23, ld=13)]
    o_n = [Op(p=['a', 'b', 3], ld=13)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 3], ld=13)]
    # TODO with consistent undo it should have been:
    # assert o_n1_l == [Op(p=['a', 'b', 3], ld=23)]

    assert o_n1_r == []


def test_json0_list_op__same_list__other_reset():
    print('====')
    d0 = {'a': {'b': [10, 11, 12, 13, 14]}}

    ################
    # new op resets after insert
    o_a = [Op(p=['a', 'b', 3], li=23)]
    o_n = [Op(p=['a', 'b', 4], li=24, ld=14)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 5], li=24, ld=14)]
    assert o_n1_r == [Op(p=['a', 'b', 5], li=24, ld=14)]

    ################
    # new op resets at the same place as insert
    o_a = [Op(p=['a', 'b', 3], li=23)]
    o_n = [Op(p=['a', 'b', 3], li=33, ld=13)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 4], li=33, ld=13)]
    assert o_n1_r == [Op(p=['a', 'b', 4], li=33, ld=13)]

    ################
    # new op resets at the same place as delete
    o_a = [Op(p=['a', 'b', 3], ld=13)]
    o_n = [Op(p=['a', 'b', 3], li=33, ld=13)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 3], li=33, ld=13)]
    assert o_n1_r == []


def test_json0_list_op__new_op_is_deeper__reset_other():
    print('====')
    d0 = {'a': {'b': [{'k': [10, 101]}, {'k': [11, 111]}, {'k': [12, 121]},
                      {'k': [13, 131]}, {'k': [14, 141]}]}}

    ################
    # new op inserts after reset
    o_a = [Op(p=['a', 'b', 3], li={'k': [23, 231]}, ld={'k': [13, 131]})]
    o_n = [Op(p=['a', 'b', 4, 'k', 0], li=44)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 4, 'k', 0], li=44)]
    assert o_n1_r == [Op(p=['a', 'b', 4, 'k', 0], li=44)]

    ################
    # new op inserts into the object that was reset
    o_a = [Op(p=['a', 'b', 3], li={'k': [23, 231]}, ld={'k': [13, 131]})]
    o_n = [Op(p=['a', 'b', 3, 'k', 0], li=33)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == []
    assert o_n1_r == []

    ################
    # new op sets a key into the object that was reset
    o_a = [Op(p=['a', 'b', 3], li={'k': [23, 231]}, ld={'k': [13, 131]})]
    o_n = [Op(p=['a', 'b', 3, 'k'], oi={'k': [33]})]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == []
    assert o_n1_r == []


def test_json0_list_op__applied_op_is_deeper__other_reset():
    print('====')
    d0 = {'a': {'b': [{'k': [10, 101]}, {'k': [11, 111]}, {'k': [12, 121]},
                      {'k': [13, 131]}, {'k': [14, 141]}]}}

    # always a trivial transform
    # unless we want a consistent undo

    ################
    # new op deletes after applied reset
    o_a = [Op(p=['a', 'b', 4, 'k', 0], li=44, ld=14)]
    o_n = [Op(p=['a', 'b', 3], ld={'k': [23, 231]})]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 3], ld={'k': [23, 231]})]
    assert o_n1_r == [Op(p=['a', 'b', 3], ld={'k': [23, 231]})]
