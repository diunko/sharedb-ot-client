import dataclasses
from dataclasses import dataclass, field
from copy import deepcopy as clone_op
from typing import Optional, Any
from delta import Delta

import logging

log = logging.getLogger('json0')


@dataclass
class Op:
    insert: Optional[Any] = None
    delete: Optional[Any] = None
    retain: Optional[Any] = None
    attributes: dict[str, Any] = field(default_factory=dict)

    _fields = {'insert', 'delete', 'retain', 'attributes'}

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

    def __repr__(self):
        return f"Op({' '.join(f'{k}={getattr(self, k)}' for k in self._fields if getattr(self, k) is not None)})"

    @property
    def insert_(self): return self.insert is not None

    @property
    def delete_(self): return self.delete is not None

    @property
    def retain_(self): return self.retain is not None

    @property
    def attributes_(self): return self.attributes is not None and len(self.attributes) != 0


class Text1:

    @staticmethod
    def apply(data: Delta, other: Delta):
        return data.compose(other)

    @staticmethod
    def transform(delta_new: Delta, delta_applied: Delta, priority='left'):
        """transform delta_new so it applies to a document with applied delta_applied"""

        # TODO: left means True or False?
        is_left = priority == 'left'
        delta_transformed = delta_new.transform(delta_applied, priority=is_left)
        return delta_transformed
