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
with `intance.context` - that will create a new, separated scope
visible inside  the decorated callable.


"""

import uuid
import sys
import typing as T

from functools import wraps
from weakref import WeakKeyDictionary


__author__ = "João S. O. Bueno"
__license__ = "LGPL v. 3.0+"

class ContextError(AttributeError):
    pass


_sentinel = object()


class _WeakId:
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


class ContextLocal:

    def __init__(self):
        super().__setattr__("_registry", WeakKeyDictionary())

    def _introspect_registry(self, name=None) -> T.Tuple[dict, T.Tuple[int, int]]:
        """
            returns the first namespace found for this context, if name is None
            else, the first namespace where the name exists. The second return
            value is a tuple inticatind the frame distance to the topmost namespace
            and the frame distance to the returned namespace.
            This way callers can tell if the searched name is on the topmost
            namespace and act accordingly. ("del" needs this information,
            as it can't remove information on an outter namespace)
        """
        f = sys._getframe(2)
        count = 0
        first_ns = None
        while f:
            hf = self._frameid(f)
            if hf in self._registry:
                if first_ns is None:
                    first_ns = count
                namespace = f.f_locals["$contexts"][self._registry[hf]]
                if name is None or name in namespace:
                    return namespace, (first_ns, count)
            f = f.f_back
            count += 1

        if name:
            raise ContextError(f"{name !r} not defined in any previous context")
        raise ContextError("No previous context set")

    def _frameid(self, frame):
        if not "$contexts_salt" in frame.f_locals:
            frame.f_locals["$contexts_salt"] = _WeakId()
        return frame.f_locals["$contexts_salt"]


    def _register_context(self, f):
        hf = self._frameid(f)
        contexts_list = f.f_locals.setdefault("$contexts", [])
        contexts_list.append({})
        self._registry[hf] = len(contexts_list) - 1

    def __getattr__(self, name):
        try:
            namespace, _ = self._introspect_registry(name)
            result = namespace[name]
            if result is _sentinel:
                raise KeyError(name)
            return result
        except (ContextError, KeyError):
            raise AttributeError(f"Attribute not set: {name}")


    def __setattr__(self, name, value):
        try:
            namespace, _ = self._introspect_registry()
        except ContextError:
            # Automatically creates a new namespace if not inside
            # any explicit denominated context:
            self._register_context(sys._getframe(1))
            namespace, _ = self._introspect_registry()

            # namespace = self._registry[hash(sys._getframe(1))] = {}
        namespace[name] = value


    def __delattr__(self, name):
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
                    del namespace[name]
                return
            # value is already shadowed:
            raise AttributeError(name)

        # Name is found, but it is not on the top-most level, so attribute is shadowed:
        setattr(self, name, _sentinel)
        namespace, _ = self._introspect_registry(name)
        namespace.setdefault("$deleted", set()).add(name)

    def context(self, callable_):
        @wraps(callable_)
        def wrapper(*args, **kw):
            f = sys._getframe()
            self._register_context(f)
            f_id = self._frameid(f)
            # f = sys._getframe()
            # self._registry[hash(f)] = {}
            result = _sentinel
            try:
                result = callable_(*args, **kw)
            finally:
                if f_id in self._registry:
                    del self._registry[f_id]
                # Setup context for generator or coroutine if one was returned:
                if result is not _sentinel:
                    frame = getattr(result, "gi_frame", getattr(result, "cr_frame", None))
                    if frame:
                        self._register_context(frame)

            return result
        return wrapper
