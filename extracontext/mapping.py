from collections.abc import MutableMapping


from .contextlocal import ContextLocal


class ContextMap(MutableMapping, ContextLocal):#, MutableMapping):
    """Works the same as ContextLocal,
    but uses the mapping interface instead of dealing with instance attributes.

    Ideal, as for most map uses, when the keys depend on data rather than
    hardcoded state variables
    """
    _BASEDIST = 1

    def __init__(self, **kwargs):
        #self.ctx = ContextLocal()
        super().__init__()
        for key, value in kwargs.items():
            self[key] = value

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



