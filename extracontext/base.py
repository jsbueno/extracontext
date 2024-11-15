# from typing import Self
from typing import cast, Any, Optional


class ContextLocal:
    _backend_registry: dict[str, type["ContextLocal"]] = {}

    def __new__(cls, *args: Any, backend: Optional[str]=None, **kwargs: Any) -> "ContextLocal":
        if backend is None:
            backend = getattr(cls, "_backend_key", "native")
        cls = cls._backend_registry[backend]
        ## Do not forward arguments to object.__new__
        if len(ContextLocal.__mro__) == 2:
            args, kwargs = (), {}
        return cast("ContextLocal", super().__new__(cls, *args, **kwargs))

    def __init__(self, *, backend: Optional[str]=None):
        pass

    def __init_subclass__(cls, *args: Any, **kw: Any) -> None:
        if hasattr(cls, "_backend_key"):
            cls._backend_registry[cls._backend_key] = cls
        super().__init_subclass__(*args, **kw)
