import dataclasses
from dataclasses import dataclass, field
from copy import deepcopy as clone_op
from typing import Optional, Any

import logging

log = logging.getLogger('json0')


@dataclass
class Op:
    p: list[str] = field(default_factory=list)
    li: Optional[Any] = None
    ld: Optional[Any] = None
    oi: Optional[Any] = None
    od: Optional[Any] = None
    na: Optional[Any] = None

    _fields = {'p', 'li', 'ld', 'oi', 'od'}

    @classmethod
    def from_dict(cls, d):
        kk = cls._fields.intersection(d)
        assert len(kk) > 0, "len(kk) > 0"
        extra = set(d.keys()).difference(cls._fields)
        if 0 < len(extra):
            log.warning(f"extra fields {extra} in decoded Op {d}")
        return Op(**{k: d[k] for k in kk})

    def to_dict(self):
        d = dataclasses.asdict(self)
        return {
            k: v
            for k, v in d.items()
            if k in self._fields and v is not None}

    def clone(self):
        return self.from_dict(clone_op(self.to_dict()))

    def __repr__(self):
        return f"Op({' '.join(f'{k}={getattr(self, k)}' for k in self._fields if getattr(self, k) is not None)})"

    @property
    def li_(self): return self.li is not None

    @property
    def ld_(self): return self.ld is not None

    @property
    def oi_(self): return self.oi is not None

    @property
    def od_(self): return self.od is not None


class Json0:

    @staticmethod
    def apply(data: dict, ops: list[Op]):
        for op in ops:
            Json0.apply_component(data, op)
        return data

    @staticmethod
    def apply_component(data: dict, op: Op):
        # find reference to operate on
        key = op.p[-1]
        path = op.p[:-1]
        ref = data
        for k in path:
            ref = ref[k]

        if op.oi_ or op.od_:
            assert type(key) == str
            assert type(ref) == dict
            if op.oi_:
                ref[key] = op.oi
            elif op.od_:
                if key in ref:
                    del ref[key]
                else:
                    log.warning('deleting non-existing key! (data=%s), (path=%s), (key=%s)',
                                data, path, key)
            else:
                assert False, f"shouldn't reach here, op: {op}"
            return

        if op.li_ and op.ld_:
            assert type(key) == int
            assert type(ref) == list
            ref[key] = op.li
            return

        if op.li_ or op.ld_:
            assert type(key) == int
            assert type(ref) == list
            if op.li_:
                ref.insert(key, op.li)
            elif op.ld_:
                ref.pop(key)
            else:
                assert False, f"shouldn't reach here, op:{op}"
            return

        assert False, f"shouldn't reach here, op: {op}"

    @staticmethod
    def transform(ops_new: list[Op], ops_applied: list[Op], priority='left'):
        """transform ops_new so it applies to a document with applied ops_applied"""
        ops_new_1 = []
        for op_n in ops_new:
            for op_a in ops_applied:
                Json0.transform_component(ops_new_1, op_n, op_a, priority)

        return ops_new_1

    @staticmethod
    def transform_component(d: list[Op], cn: Op, ca: Op, priority='left'):
        """transform c_n so it applies to a document with c_a applied."""

        if ca.li_ and ca.ld_:
            return Json0.transform_component_l_op_a_reset(d, cn, ca, priority)
        if cn.li_ and cn.ld_:
            return Json0.transform_component_l_op_n_reset(d, cn, ca, priority)
        if ca.li_ or ca.ld_:
            return Json0.transform_component_l_op(d, cn, ca, priority)
        if ca.oi_ or ca.od_:
            return Json0.transform_component_o_op(d, cn, ca, priority)
        else:
            assert False, "don't support other cases for now"

    @staticmethod
    def transform_component_l_op_a_reset(d: list[Op], cn: Op, ca: Op, priority='left'):
        p_common = common_path(ca, cn)
        la = len(ca.p)
        ln = len(cn.p)
        lc = len(p_common)
        cn1 = clone_op(cn)

        assert ca.li_ and ca.ld_

        # is cn operating on/under the same list as ca?
        if lc == la or lc == la - 1:
            # lc == la means (lc == la <= ln)
            #   cn.p is exactly the same or narrower as ca.p

            # lc == la - 1 example:
            #   ca.p == ['a','b','c',3]
            #   cn.p == ['a','b','c',4,'d']
            pass
        else:
            # lc < la - 1 means that cn.p is strictly broader then or non-intersecting with ca.p
            d.append(cn1)
            return d

        i_n = cn.p[la - 1]
        i_a = ca.p[la - 1]
        assert type(i_n) == int and type(i_a) == int

        if i_a != i_n:
            # no intersection
            d.append(cn1)
            return d
        elif i_a == i_n:
            if la == lc == ln:
                if cn.li_ and cn.ld_:
                    # two reset ops at the same path
                    # select which wins by priority
                    if priority == 'left':
                        d.append(cn1)
                        return d
                    else:
                        # discard cn
                        return d
                elif cn.ld_:
                    if priority == 'left':
                        d.append(cn1)
                        return d
                    else:
                        # applied reset overrides a delete
                        # discard cn
                        return d
                else:
                    d.append(cn1)
                    return d
            elif la < ln:
                # discard cn
                return d
            elif ln < la:
                # means cn is strictly broader
                assert False, "shouldn't reach here"
        assert False, "shouldn't reach here"

    @staticmethod
    def transform_component_l_op_n_reset(d: list[Op], cn: Op, ca: Op, priority='left'):
        p_common = common_path(ca, cn)
        la = len(ca.p)
        ln = len(cn.p)
        lc = len(p_common)
        cn1 = clone_op(cn)

        assert (cn.li_ and cn.ld_  # cn is reset
                and (ca.li_ or ca.ld_)  # ca is list op
                and not (ca.li_ and ca.ld_))  # ca is not reset

        # is cn operating on/under the same list as ca?
        if lc == la or lc == la - 1:
            # lc == la means (lc == la <= ln)
            #   cn.p is exactly the same or narrower as ca.p

            # lc == la - 1 example:
            #   ca.p == ['a','b','c',3]
            #   cn.p == ['a','b','c',4,'d']
            pass
        else:
            # lc < la - 1 means that cn.p is strictly broader then or non-intersecting with ca.p
            d.append(cn1)
            return d

        i_n = cn.p[la - 1]
        i_a = ca.p[la - 1]
        assert type(i_n) == int and type(i_a) == int

        # when do we have to unconditionally discard cn?
        #   an is a delete broader then cn
        #
        # when do we have to resolve conflict?
        #   for the same path, an is delete cn is reset
        #
        # when do we have to shift index on cn?
        #   cn is for same/later index then ca
        #
        # everything else leaves cn the same

        # unconditionally discard cn:
        #   an is a delete broader then cn
        if la <= lc < ln and ca.ld_:
            # discard cn
            return d

        # resolve conflict:
        #   for the same path, an is delete cn is reset
        if la == lc == ln and ca.ld_:
            if priority == 'left':
                d.append(cn1)
                return d
            else:
                return d

        # when do we have to shift index on cn?
        #   cn is for same/later index then ca
        if i_a <= i_n:
            if ca.ld_:
                cn1.p[la - 1] -= 1
            elif ca.li_:
                cn1.p[la - 1] += 1
            else:
                assert False, "shouldn't reach here"
            d.append(cn1)
            return d

        # everything else leaves cn the same
        d.append(cn1)
        return d

    @staticmethod
    def transform_component_l_op(d: list[Op], cn: Op, ca: Op, priority='left'):
        p_common = common_path(ca, cn)
        la = len(ca.p)
        ln = len(cn.p)
        lc = len(p_common)
        cn1 = clone_op(cn)

        assert (ca.li_ or ca.ld_) and not (ca.li_ and ca.ld_)

        # is cn operating on/under the same list as ca?
        if lc == la or lc == la - 1:
            # lc == la means (lc == la <= ln)
            #   cn.p is exactly the same or narrower as ca.p

            # lc == la - 1 example:
            #   ca.p == ['a','b','c',3]
            #   cn.p == ['a','b','c',4,'d']
            pass
        else:
            # lc < la - 1 means that cn.p is strictly broader then or non-intersecting with ca.p
            d.append(cn1)
            return d

        i_n = cn.p[la - 1]
        i_a = ca.p[la - 1]
        assert type(i_n) == int and type(i_a) == int

        if ca.li_:
            # shift cn index if it's affected by the insert
            if i_n == i_a and (priority == 'right' or cn.ld_ or lc < ln):
                cn1.p[la - 1] += 1
            if i_a < i_n:
                cn1.p[la - 1] += 1

            d.append(cn1)
            return d

        if ca.ld_:
            # shift cn index if it's affected by the delete
            if i_n < i_a:
                d.append(cn1)
                return d
            if i_n == i_a:
                if la == lc == ln and cn.li_:
                    # cn inserts element at the same index that was deleted
                    # no change in cn
                    d.append(cn1)
                    return d
                else:
                    # the element that cn wants to operate on was deleted
                    # discard cn
                    return d
            if i_a < i_n:
                cn1.p[la - 1] -= 1
                d.append(cn1)
                return d

        assert False, "shouldn't reach here"

    def transform_component_o_op(d: list[Op], cn: Op, ca: Op, priority='left'):
        p_common = common_path(ca, cn)
        la = len(ca.p)
        ln = len(cn.p)
        lc = len(p_common)
        cn1 = clone_op(cn)

        # is cn operating on/under the same object as ca?
        if la <= lc <= ln:
            pass
        else:
            assert lc < la and lc < ln, f"(lc < la and lc < ln) ca: {ca}, cn: {cn}"

            # cn and ca commute as they operate on different paths
            d.append(cn1)
            return d

        if ca.oi_:
            if la == ln == lc:
                # both are trying to set the same key
                if priority == 'left':
                    # cn is left, so it wins
                    d.append(cn1)
                    return d
                elif priority == 'right':
                    # discard cn
                    return d
            if la == lc < ln:
                # object that cn wants to operate on, was reset by ca
                # discard cn
                return d

            assert False, f"shouldn't reach here, ca: {ca},  cn: {cn}"

        if ca.od_:
            if la == lc == ln:
                if cn.od_:
                    # nothing to do
                    return d

                assert cn.oi_, f'Op should have oi {cn}'
                if priority == 'left':
                    d.append(cn1)
                return d

            if la == lc < ln:
                # object that cn wants to operate on, was reset by ca
                # discard cn
                return d

            assert False, f"shouldn't reach here, ca: {ca},  cn: {cn}"

        assert False, f"shouldn't reach here, ca: {ca},  cn: {cn}"


def common_path(op1: Op, op2: Op):
    p = []
    for c1, c2 in zip(op1.p, op2.p):
        if c1 != c2:
            break
        p.append(c1)
    return p


def dict_as_ops(d: dict, prefix=None, ops=None):
    prefix = prefix or []
    ops = ops or []

    for k, v in d.items():
        if type(v) == dict:
            prefix1 = prefix + [k]
            ops.append(Op(p=prefix1, oi={}))
            dict_as_ops(v, prefix1, ops)
        else:
            op = Op(**{'p': prefix + [k], 'oi': v})
            ops.append(op)
    return ops
