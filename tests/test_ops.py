from dataclasses import dataclass, asdict
from sharedb.doc import Doc, Op, DocOp


def test_ops_basic():
    print('====' * 8)

    d = Doc.create_({
        'profile': {
            'ava': 'bla.jpg',
            'nickname': 'test'},
        'items': [
            {'id': 123,
             'selected': True,
             'content': 'testing 123'}]},
        id='doc-foo',
        coll_id='coll-bar'
    )

    op = Op(p=['profile', 'nickname'], oi='qux')
    d.apply([op])
    assert d.data['profile'] == {'ava': 'bla.jpg', 'nickname': 'qux'}

    d_o_send = d._shift_op()
    # .... send to network, wait for ack
    d._ack(d_o_send.op_id, d_o_send.v)
    d_o_test = DocOp(
        v=1, d='doc-foo', c='coll-bar',
        op_id=f'{d.cli_id}-{0}',
        op=[op],
    )

    assert asdict(d_o_send) == asdict(d_o_test)
