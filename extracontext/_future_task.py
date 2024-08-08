"""
Code backported from Python 3.12:
Task.__init__ will accept a "contxt" parameter that is needed
in order to re-use contexts for async generator iterations.


The subclass is created in order for the minimal of "copy-pasting" around
to be needed.

# **** License for this file: PSF License - ****
"""

import itertools
from asyncio.tasks import _PyTask, _register_task

# from asyncio import futures

from asyncio import coroutines


_task_name_counter = itertools.count(1).__next__


class FutureTask(_PyTask):
    # Just overrides __init__ with Python 3.12 _PyTask.__init__,
    # which accepts the context as argument

    def __init__(self, coro, *, loop=None, name=None, context=None, eager_start=False):
        # skip Python < 3.10 Task.__init__ :
        super(_PyTask, self).__init__(loop=loop)
        if self._source_traceback:
            del self._source_traceback[-1]
        if not coroutines.iscoroutine(coro):
            # raise after Future.__init__(), attrs are required for __del__
            # prevent logging for pending task in __del__
            self._log_destroy_pending = False
            raise TypeError(f"a coroutine was expected, got {coro!r}")

        if name is None:
            self._name = f"FutureTask-{_task_name_counter()}"
        else:
            self._name = str(name)

        self._num_cancels_requested = 0
        self._must_cancel = False
        self._fut_waiter = None
        self._coro = coro
        if context is None:
            # this is the only codepath in Python < 3.10, and the reason for this hack:
            self._context = contextvars.copy_context()
        else:
            self._context = context

        if eager_start and self._loop.is_running():
            self.__eager_start()
        else:
            self._loop.call_soon(self._Task__step, context=self._context)
            _register_task(self)
