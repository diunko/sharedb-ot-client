from sharedb.ot.json0 import Op, Json0


def test_json0_list_op__same_list__insert_insert():
    print('====')
    d0 = {'a': {'b': [10, 11, 12, 13, 14]}}

    ################
    # new op inserts after applied
    o_a = [Op(p=['a', 'b', 3], li=23)]
    o_n = [Op(p=['a', 'b', 4], li=34)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 5], li=34)]
    assert o_n1_r == [Op(p=['a', 'b', 5], li=34)]

    ################
    # new op inserts before applied
    o_a = [Op(p=['a', 'b', 3], li=23)]
    o_n = [Op(p=['a', 'b', 2], li=32)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 2], li=32)]
    assert o_n1_r == [Op(p=['a', 'b', 2], li=32)]

    ################
    # new op inserts at the same place as applied
    o_a = [Op(p=['a', 'b', 3], li=23)]
    o_n = [Op(p=['a', 'b', 3], li=33)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 3], li=33)]
    assert o_n1_r == [Op(p=['a', 'b', 4], li=33)]


def test_json0_list_op__same_list__insert_delete():
    print('====')
    d0 = {'a': {'b': [10, 11, 12, 13, 14]}}

    ################
    # new op deletes after applied
    o_a = [Op(p=['a', 'b', 3], li=23)]
    o_n = [Op(p=['a', 'b', 4], ld=14)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 5], ld=14)]
    assert o_n1_r == [Op(p=['a', 'b', 5], ld=14)]

    ################
    # new op deletes before applied
    o_a = [Op(p=['a', 'b', 3], li=23)]
    o_n = [Op(p=['a', 'b', 2], ld=12)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 2], ld=12)]
    assert o_n1_r == [Op(p=['a', 'b', 2], ld=12)]

    ################
    # new op deletes at the same place as applied
    o_a = [Op(p=['a', 'b', 3], li=23)]
    o_n = [Op(p=['a', 'b', 3], ld=13)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 4], ld=13)]
    assert o_n1_r == [Op(p=['a', 'b', 4], ld=13)]


def test_json0_list_op__same_list__delete_insert_0():
    print('====')
    d0 = {'a': {'b': [10, 11, 12, 13, 14]}}

    ################
    # new op inserts after applied
    o_a = [Op(p=['a', 'b', 3], ld=13)]
    o_n = [Op(p=['a', 'b', 4], li=24)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 3], li=24)]
    assert o_n1_r == [Op(p=['a', 'b', 3], li=24)]

    ################
    # new op inserts before applied
    o_a = [Op(p=['a', 'b', 3], ld=13)]
    o_n = [Op(p=['a', 'b', 2], li=22)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 2], li=22)]
    assert o_n1_r == [Op(p=['a', 'b', 2], li=22)]


def test_json0_list_op__same_list__delete_insert_1():
    print('====')
    d0 = {'a': {'b': [10, 11, 12, 13, 14]}}

    ################
    # new op inserts at the same place as deleted
    o_a = [Op(p=['a', 'b', 3], ld=13)]
    o_n = [Op(p=['a', 'b', 3], li=23)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 3], li=23)]
    assert o_n1_r == [Op(p=['a', 'b', 3], li=23)]


def test_json0_list_op__same_list__delete_delete():
    print('====')
    d0 = {'a': {'b': [10, 11, 12, 13, 14]}}

    ################
    # new op deletes after applied
    o_a = [Op(p=['a', 'b', 3], ld=13)]
    o_n = [Op(p=['a', 'b', 4], ld=14)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 3], ld=14)]
    assert o_n1_r == [Op(p=['a', 'b', 3], ld=14)]

    ################
    # new op deletes before applied
    o_a = [Op(p=['a', 'b', 3], ld=13)]
    o_n = [Op(p=['a', 'b', 2], ld=12)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 2], ld=12)]
    assert o_n1_r == [Op(p=['a', 'b', 2], ld=12)]

    ################
    # new op deletes at the same place as applied
    o_a = [Op(p=['a', 'b', 3], ld=13)]
    o_n = [Op(p=['a', 'b', 3], ld=13)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == []
    assert o_n1_r == []


def test_json0_list_op__new_op_is_deeper__delete_other():
    print('====')
    d0 = {'a': {'b': [{'k': [10, 101]}, {'k': [11, 111]}, {'k': [12, 121]},
                      {'k': [13, 131]}, {'k': [14, 141]}]}}

    ################
    # new op inserts after applied
    o_a = [Op(p=['a', 'b', 3], ld={'k': [13, 131]})]
    o_n = [Op(p=['a', 'b', 4, 'k', 0], li=24)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 3, 'k', 0], li=24)]
    assert o_n1_r == [Op(p=['a', 'b', 3, 'k', 0], li=24)]

    ################
    # new op inserts before applied
    o_a = [Op(p=['a', 'b', 3], ld={'k': [13, 131]})]
    o_n = [Op(p=['a', 'b', 2, 'k', 0], li=22)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 2, 'k', 0], li=22)]
    assert o_n1_r == [Op(p=['a', 'b', 2, 'k', 0], li=22)]

    ################
    # new op inserts at the same place as applied
    o_a = [Op(p=['a', 'b', 3], ld={'k': [13, 131]})]
    o_n = [Op(p=['a', 'b', 3, 'k', 0], li=24)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == []
    assert o_n1_r == []


def test_json0_list_op__new_op_is_deeper__insert_other():
    print('====')
    d0 = {'a': {'b': [{'k': [10, 101]}, {'k': [11, 111]}, {'k': [12, 121]},
                      {'k': [13, 131]}, {'k': [14, 141]}]}}

    ################
    # new op inserts after applied
    o_a = [Op(p=['a', 'b', 3], li={'k': [23, 231]})]
    o_n = [Op(p=['a', 'b', 4, 'k', 0], li=44)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 5, 'k', 0], li=44)]
    assert o_n1_r == [Op(p=['a', 'b', 5, 'k', 0], li=44)]

    ################
    # new op inserts before applied
    o_a = [Op(p=['a', 'b', 3], li={'k': [23, 231]})]
    o_n = [Op(p=['a', 'b', 2, 'k', 0], li=22)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 2, 'k', 0], li=22)]
    assert o_n1_r == [Op(p=['a', 'b', 2, 'k', 0], li=22)]

    ################
    # new op inserts at the same place as applied
    o_a = [Op(p=['a', 'b', 3], li={'k': [23, 231]})]
    o_n = [Op(p=['a', 'b', 3, 'k', 0], li=33)]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 4, 'k', 0], li=33)]
    assert o_n1_r == [Op(p=['a', 'b', 4, 'k', 0], li=33)]


def test_json0_list_op__applied_op_is_deeper__other_delete():
    print('====')
    d0 = {'a': {'b': [{'k': [10, 101]}, {'k': [11, 111]}, {'k': [12, 121]},
                      {'k': [13, 131]}, {'k': [14, 141]}]}}

    # always a trivial transform
    # unless we want a consistent undo

    ################
    # new op deletes after applied
    o_a = [Op(p=['a', 'b', 4, 'k', 0], li=44)]
    o_n = [Op(p=['a', 'b', 3], ld={'k': [23, 231]})]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 3], ld={'k': [23, 231]})]
    assert o_n1_r == [Op(p=['a', 'b', 3], ld={'k': [23, 231]})]

    ################
    # new op deletes at the same place as applied
    o_a = [Op(p=['a', 'b', 4, 'k', 0], li=44)]
    o_n = [Op(p=['a', 'b', 4], ld={'k': [14, 141]})]

    o_n1_l = Json0.transform(o_n, o_a, priority='left')
    o_n1_r = Json0.transform(o_n, o_a, priority='right')

    assert o_n1_l == [Op(p=['a', 'b', 4], ld={'k': [14, 141]})]
    assert o_n1_r == [Op(p=['a', 'b', 4], ld={'k': [14, 141]})]

    # TODO with consistent undo it should have been:
    # assert o_n1_l == [Op(p=['a', 'b', 4], ld={'k': [44, 14, 141]})]
    # assert o_n1_r == [Op(p=['a', 'b', 4], ld={'k': [44, 14, 141]})]
