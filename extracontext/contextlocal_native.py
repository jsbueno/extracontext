"""
Super context wrapper -

Meant to have the same interface as the easy-to-use ContextLocal,
implemented 100% in Python, but backed by PEP 567 stdlib contextvar.ContextVar


"""

import uuid
import sys
import typing as T

from functools import wraps
from weakref import WeakKeyDictionary
from contextvars import ContextVar, Context, copy_context


__author__ = "João S. O. Bueno"
__license__ = "LGPL v. 3.0+"

class ContextError(AttributeError):
    pass


_sentinel = object()


class NativeContextLocal:
    """Uses th native contextvar module in the stdlib (PEP 567)
    to provide a context-local namespace in the way
    threading.local  works for threads.

    Assignements and reading from the namespace
    should work naturally with no need to call `get` and `set` methods.

    In contrast to the pure-Python implementation there are
    some limitations,such as the impossibility to work
    in as a contextmanager (Python `with` block),.

    [Work In Progress]
    """
    def __init__(self):
        self._registry = {}



    def __getattr__(self, name):
        var = self._registry.get(name, None)
        if var is None:
            raise AttributeError(f"Attribute not set: {name}")
        value = var.get()
        if value is _sentinel:
            raise AttributeError(f"Attribute not set: {name}")
        return value


    def __setattr__(self, name, value):
        if name.startswith("_"):
            return super().__setattr__(name, value)
        var = self._registry.get(name, None)
        if var is None:
            var = self._registry[name] = ContextVar(name)
        var.set(value)


    def __delattr__(self, name):
        if getattr(self, name, _sentinel) is _sentinel:
            raise AttributeError(f"Attribute not set: {name}")
        setattr(self, name, _sentinel)

    def __call__(self, callable_):
        @wraps(callable_)
        def wrapper(*args, **kw):
            return self._run(callable_, *args, **kw)
        return wrapper

    def __enter__(self):
        raise NotImplementedError("Context manager behavior not implemented by native ContextVars implementation")

    def __exit__(self, exc_type, exc_value, traceback):
        raise NotImplementedError("Context manager behavior not implemented by native ContextVars implementation")

    def _run(self, callable_, *args, **kw):
        """Runs callable with an isolated context
        no need to decorate the target callable
        """
        new_context = copy_context()
        return new_context.run(callable_, *args, **kw)


    def __dir__(self):
        return list(self._registry.keys())
