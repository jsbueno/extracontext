from collections.abc import Mapping, MutableMapping
from typing import Optional

from .base import ContextLocal
from .contextlocal import PyContextLocal
from .contextlocal_native import NativeContextLocal


class ContextMap(MutableMapping, ContextLocal):
    """Works the same as PyContextLocal,
    but uses the mapping interface instead of dealing with instance attributes.

    Ideal, as for most map uses, when the keys depend on data rather than
    hardcoded state variables
    """

    _backend_registry = {}

    # def __init__(self, initial: None | Mapping = None, *, backend=None):
    # super().__init__()
    # if not initial:
    # return
    # for key, value in initial.items():
    # self[key] = value

    def __getitem__(self, name):
        try:
            return self.__getattr__(name)
        except AttributeError:
            raise KeyError(name)

    def __setitem__(self, name, value):
        setattr(self, name, value)

    def __delitem__(self, name):
        try:
            delattr(self, name)
        except AttributeError:
            raise KeyError(name)

    def __iter__(self):
        return iter(dir(self))

    def __len__(self):
        return len(dir(self))


class PyContextMap(ContextMap, PyContextLocal):
    _backend_key = "python"
    _BASEDIST = 1

    def __init__(self, initial: Optional[Mapping] = None, *, backend=None):
        super().__init__()
        if not initial:
            return
        try:
            self._BASEDIST = 2
            for key, value in initial.items():
                self[key] = value
        finally:
            del self._BASEDIST


class NativeContextMap(ContextMap, NativeContextLocal):
    _backend_key = "native"

    def __init__(self, initial: Optional[Mapping] = None, *, backend=None):
        super().__init__()
        if not initial:
            return
        for key, value in initial.items():
            self[key] = value
