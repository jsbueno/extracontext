class ContextLocal:
    _backend_registry = {}

    def __new__(cls, *args, backend=None, **kwargs):
        if backend is None:
            backend = getattr(cls, "_backend_key", "native")

        cls = cls._backend_registry[backend]
        ## Do not forward arguments to object.__new__
        if len(__class__.__mro__) == 2:
            args, kwargs = (), {}
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *, backend=None):
        pass

    def __init_subclass__(cls, *args, **kw):
        if hasattr(cls, "_backend_key"):
            cls._backend_registry[cls._backend_key] = cls
        super().__init_subclass__(*args, **kw)
