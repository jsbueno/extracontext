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
from concurrent.futures import ThreadPoolExecutor


class ContextPreservingExecutor(ThreadPoolExecutor):
    # [WIP]
    ...
