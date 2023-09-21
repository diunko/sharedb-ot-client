from dataclasses import dataclass, asdict
from sharedb.doc import Doc, Op, DocOp
import sharedb.protocol as proto


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
    d.v = 1  # as if it was acked by server

    op = Op(p=['profile', 'nickname'], oi='qux')
    d.apply([op])
    assert d.data['profile'] == {'ava': 'bla.jpg', 'nickname': 'qux'}

    d_o_send_msg = d._shift_op_msg()
    # .... send to network, wait for ack
    d._ack_msg(d_o_send_msg)
    d_o_test_msg = proto.Op(
        v=1, d='doc-foo', c='coll-bar',
        src=d_o_send_msg.src, seq=d_o_send_msg.seq,
        op=[op],
    )

    assert asdict(d_o_send_msg) == asdict(d_o_test_msg)
