"""
Super context wrapper -

meant to be simpler to use and work in more scenarios than
Python's contextvars.

Usage:
Create one or more project-wide instances of "ContextLocal"
Decorate your functions, co-routines, worker-methods and generators
that should hold their own states with that instance's `context` method -

and use the instance as namespace for private variables that will be local
and non-local until entering another callable decorated
with that instance - that will create a new, separated scope
visible inside  the decorated callable.


"""

import uuid
import sys
import typing as T

from functools import wraps
from types import FrameType
from weakref import WeakKeyDictionary

from .base import ContextLocal

__author__ = "João S. O. Bueno"
__license__ = "LGPL v. 3.0+"

class ContextError(AttributeError):
    pass


_sentinel = object()


class _WeakableId:
    """Used internally to identify Frames with context data attached using weakrefs
    """

    __slots__ = ["__weakref__", "value"]
    def __init__(self, v=0):
        if not v:
            v = int(uuid.uuid4())
        self.value = v

    def __eq__(self, other):
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return f"ID({uuid.UUID(int=self.value)})"


class PyContextLocal(ContextLocal):
    """Creates a namespace object whose attributes can keep individual and distinct values for
    the same key for code running in parallel - either in asyncio tasks, or threads.

    The bennefits are the same one gets by using contextvars.ContextVar from the stdlib as
    specified on PEP 567. However extracontext.ContextLocal is designed to be easier
    and more convenient to use - as a single instance can hold values for several
    keys, just as happens with threading.local objects. And no special getter and
    setter methods are needed to retrieve the unique value stored in the current
    context: normal attribute access and assignment works transparently.

    Internally, the current implementation uses a completly different way to
    keep distinct states where needed: the "locals" mapping for each execution
    frame is used as storage for the unique values in an async task context, or in
    a thread. Although not recomended up to now, read/write access to non-local-variables
    in the "locals" mapping is specified on PEP 558. While that PEP is not
    final, it is clear in its texts that the capability of using "locals" as
    a mapping to convey data will be kept and made official.

    References to the frames containing context data is kept using
    weakreferences, so when a Frame ends up execution, its contents
    are deleted normally, with no risks of frame data
    hanging around due to PyContextLocal data.


    """

    # TODO: change _BASEDIST to a property counting the intermediate
    # methods between subclasses and the methods here.
    _BASEDIST = 0

    _backend_key = "python"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().__setattr__("_registry", WeakKeyDictionary())

    def _introspect_registry(self, name: T.Optional[str]=None, starting_frame: int=2) -> T.Tuple[dict, T.Tuple[int, int]]:
        """
            returns the first namespace found for this context, if name is None
            else, the first namespace where the name exists. The second return
            value is a tuple inticatind the frame distance to the topmost namespace
            and the frame distance to the returned namespace.
            This way callers can tell if the searched name is on the topmost
            namespace and act accordingly. ("del" needs this information,
            as it can't remove information on an outter namespace)
        """
        starting_frame += self._BASEDIST
        f: T.Optional[FrameType] = sys._getframe(starting_frame)
        count = 0
        first_ns = None
        while f:
            hf = self._frameid(f)
            if hf in self._registry:
                if first_ns is None:
                    first_ns = count
                registered_namespaces = f.f_locals["$contexts"]
                for namespace_index in reversed(self._registry[hf]):
                    namespace = registered_namespaces[namespace_index]
                    if name is None or name in namespace:
                        return namespace, (first_ns, count)
                    count += 1
            f = f.f_back

        if name:
            raise ContextError(f"{name !r} not defined in any previous context")
        raise ContextError("No previous context set")

    def _frameid(self, frame: FrameType) -> _WeakableId:
        if not "$contexts_salt" in frame.f_locals:
            frame.f_locals["$contexts_salt"] = _WeakableId()
        return frame.f_locals["$contexts_salt"]


    def _register_context(self, f: FrameType) -> None:
        hf = self._frameid(f)
        contexts_list = f.f_locals.setdefault("$contexts", [])
        contexts_list.append({})
        self._registry.setdefault(hf, []).append(len(contexts_list) - 1)

    def _pop_context(self, f: FrameType) -> None:
        hf = self._frameid(f)
        context_being_popped = self._registry[hf].pop()
        contexts_list = f.f_locals["$contexts"]
        contexts_list[context_being_popped] = None


    def __getattr__(self, name: str) -> T.Any:
        try:
            namespace, _ = self._introspect_registry(name)
            result = namespace[name]
            if result is _sentinel:
                raise KeyError(name)
            return result
        except (ContextError, KeyError):
            raise AttributeError(f"Attribute not set: {name}")


    def __setattr__(self, name: str, value: T.Any) -> None:
        try:
            namespace, _ = self._introspect_registry()
        except ContextError:
            # Automatically creates a new namespace if not inside
            # any explicit denominated context:
            self._register_context(sys._getframe(1 + self._BASEDIST))
            namespace, _ = self._introspect_registry()

        namespace[name] = value


    def __delattr__(self, name: str) -> None:
        try:
            namespace, (topmost_ns, found_ns) = self._introspect_registry(name)
        except ContextError:
            raise AttributeError(name)
        if topmost_ns == found_ns:
            result = namespace[name]
            if result is not _sentinel:
                if "$deleted" in namespace and name in namespace["$deleted"]:
                    # attribute exists in target namespace, but the outter
                    # attribute had previously been shadowed by a delete -
                    # restore the shadowing:
                    setattr(self, name, _sentinel)

                else:
                    # Remove topmost name assignemnt, and outer value is exposed
                    # ("one_level" attribute stacking behavior as described in 'features.py'
                    # disbled as unecessaryly complex):
                    # del namespace[name]

                    # To preserve  "entry_only" behavior:
                    namespace.setdefault("$deleted", set()).add(name)
                    setattr(self, name, _sentinel)
                return
            # value is already shadowed:
            raise AttributeError(name)

        # Name is found, but it is not on the top-most level, so attribute is shadowed:
        setattr(self, name, _sentinel)
        # fossil: namespace, _ = self._introspect_registry(name)
        namespace.setdefault("$deleted", set()).add(name)

    def __call__(self, callable_: T.Callable) -> T.Callable:
        @wraps(callable_)
        def wrapper(*args, **kw):
            f = sys._getframe()
            self._register_context(f)
            f_id = self._frameid(f)
            result = _sentinel
            try:
                result = callable_(*args, **kw)
            finally:
                if f_id in self._registry:
                    del self._registry[f_id]
                # Setup context for generator, async generator or coroutine if one was returned:
                if result is not _sentinel:
                    frame = None
                    for frame_attr in ("gi_frame", "ag_frame", "cr_frame"):
                        frame = getattr(result, frame_attr, None)
                        if frame:
                            self._register_context(frame)
            return result
        return wrapper

    def __enter__(self):
        self._register_context(sys._getframe(1))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._pop_context(sys._getframe(1))

    def _run(self, callable_, *args, **kw):
        """Runs callable with an isolated context
        no need to decorate the target callable
        """
        with self:
            return callable_(*args, **kw)


    def __dir__(self) -> T.List[str]:
        frame_count = 2
        all_attrs = set()
        seen_namespaces = set()
        while True:
            try:
                namespace, _ = self._introspect_registry(starting_frame=frame_count)
            except (ValueError, ContextError):  # ValueError can be raised sys._getframe inside _introspect_registry
                break
            frame_count += 1
            if id(namespace) in seen_namespaces:
                continue
            for key, value in namespace.items():
                if not key.startswith("$") and value is not _sentinel:
                    all_attrs.add(key)

            seen_namespaces.add(id(namespace))
        all_attrs = (attr for attr in all_attrs if getattr(self, attr, _sentinel) is not _sentinel)
        return sorted(all_attrs)
