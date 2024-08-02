import threading
import time
from collections import deque

import pytest

from extracontext import ContextLocal, NativeContextLocal

consume = deque(maxlen=0).extend


@pytest.mark.parametrize(["ContextClass"], [
    (ContextLocal,),
    (NativeContextLocal,)
])
def test_context_local_vars_work_for_threads(ContextClass):

    ctx = ContextClass()

    results = set()

    @ctx
    def worker(value):
        ctx.value = value
        time.sleep((10 - value) * 0.01)
        assert value == ctx.value
        results.add(ctx.value)

    @ctx
    def manager():
        ctx.value = -1
        tasks = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        consume(t.start() for t in tasks)
        consume(t.join() for t in tasks)
        assert all(i in results for i in range(10))
        assert ctx.value == -1

    manager()
