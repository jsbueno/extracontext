import threading
import time
from collections import deque

from extracontext import ContextLocal

consume = deque(maxlen=0).extend


def test_context_local_vars_work_for_threads():


    ctx = ContextLocal()

    results = set()

    @ctx.context
    def worker(value):
        ctx.value = value
        time.sleep((10 - value) * 0.01)
        assert value == ctx.value
        results.add(ctx.value)

    @ctx.context
    def manager():
        ctx.value = -1
        tasks = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        consume(t.start() for t in tasks)
        consume(t.join() for t in tasks)
        assert all(i in results for i in range(10))
        assert ctx.value == -1

    manager()
