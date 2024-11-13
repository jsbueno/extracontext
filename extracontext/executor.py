"""
Subclass of ThreadPoolExecutor which adds information
obout the context a task is submited on in the call,
and enters that context in the worker thread prior
to running its code.


This would be a simple matter of overriding a few
methods and add a couple lines in ThreadPoolExecutor
itself - but since it was not built with
subclassing in mind, a hack is needed so that
the executor uses the appropriate _WorkItem
subclass required for switching context.


"""

import asyncio
import inspect
import sys
import threading

import concurrent.futures
import concurrent.futures.thread
import contextvars
from concurrent.futures import ThreadPoolExecutor
from types import FunctionType


# Our _WorkItem subclass: just
# ordinary overriding adding a context attribute:

class _CustomWorkItem(concurrent.futures.thread._WorkItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._context = contextvars.copy_context()

    def run(self):
        ctx = self._context.copy()
        result = ctx.run(super().run)
        return result


original_submit = ThreadPoolExecutor.submit
new_globals = concurrent.futures.thread.__dict__.copy()
new_globals["_WorkItem"] = _CustomWorkItem


# TODO: assert .submit makes use of _WorkItem
new_submit = FunctionType(original_submit.__code__, new_globals)



class ContextPreservingExecutor(ThreadPoolExecutor):
    """Drop in context preserving replacement to concurrent.futures.ThreadPoolExecutor

    This class adds a missing functionality to asynchorous coding in Python,
    in which separate tasks will naturally each have their own context
    with distinct contextvars (either native stdlib scalar contextvars
    or extracontext.ContextLocal namespaces): when calling a blocking
    function with "run_in_executor", the context is zeroed-out in the
    function executed in any of the worker threads.

    By simply instantiating this class for an Executor, the called
    functions will run in a copy of the same context that was in use
    by the callee - which means one is free to use `await loop.run_in_executor`
    calls and have the target function still see the current context.

    """
    submit = new_submit


