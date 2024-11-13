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
    submit = new_submit


