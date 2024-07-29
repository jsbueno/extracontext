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
import contextvars


__author__ = "João S. O. Bueno"
__license__ = "LGPL v. 3.0+"

class ContextError(AttributeError):
    pass

class TopLevelAbort(Exception):
    ...

class ResetToTopLevel(BaseException):
    ...

_sentinel = object()


class NativeContextLocal:
    """Uses th native contextvar module in the stdlib (PEP 567)
    to provide a context-local namespace in the way
    threading.local  works for threads.

    Assignements and reading from the namespace
    should work naturally with no need to call `get` and `set` methods.

    # In contrast to the pure-Python implementation there are
    # some limitations,such as the impossibility to work
    # in as a contextmanager (Python `with` block),.

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
        return list(key for key, value in self._registry.items() if value.get() is not _sentinel)

class _Context:
    """ HACK: Allows the use of Python contextvar functionality
    within a context manager (used by the `with` statement),
    without having to resort to code to copy the context, and have a trampoline function
    to change context entries, before making a call needing
    the nested values.

    Disclaimer: the context copy and trampoline are still needed,
    but are internal to the uber-hacky, trace-setting, Frame fiddling implmentation
    herein implemented
    """
    frame_tracker = contextvars.ContextVar("tracker", default=False)


    def jumper(self, caller_frame):
        self.frame_tracker.set(self.tracker, caller_frame)
        sys.settrace(self.trace_call)
        code = caller_frame.f_code

        function = FunctionType(code, caller_frame.f_globals, closure=())
        argcount = code.co_argcount
        kwargcount = code.co_kwonlyargcount

        # Code to call a function recreated from the code object, passing
        #bogus numeric values. (If someone had the brilliant idea
                               #of enforcing annotations at runtime
                               #this will break)

        # settrace
        try:
            result = function(*range(argcount), **{k: v for k, v in zip(code.co_varnames[argcount: argcount + kwargcount], range(kwargcount))})
        except ResetToTopLevel: # raised on nested __exit__
            pass
        sys.settrace(None)
        return

    def __enter__(self):
        if ctx:=cls.frame_tracker.get():
            ...
            return ctx
        ctx = contextvars.copy_context()
        frame = sys._getframe(1)
        ctx.run(self.jumper, frame)
        # TODO: raising TopLevelAbort won't do-
        # the settrace "goto" trick has to be used again
        raise ToplevelAbort()
    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is ToplevelAbort:
            # TODO: update caller frame locals
            return True
        if ctx:=cls.tracker.get():
            frame = sys._getframe(1)
            self.frame_tracker.get().f_locals.update(frame.f_locals)
            raise ResetToTopLevel
