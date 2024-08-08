import threading
import time
from collections import deque

import pytest

from extracontext import PyContextLocal, NativeContextLocal

consume = deque(maxlen=0).extend


@pytest.mark.parametrize(["ContextClass"], [(PyContextLocal,), (NativeContextLocal,)])
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


@pytest.mark.parametrize(["ContextClass"], [(PyContextLocal,), (NativeContextLocal,)])
def test_root_value_do_not_exists_on_new_thread(ContextClass):
    # Variable unset in the namespace in a new thread is the
    # behavior for threading.local and contextvar.ContextVar:
    ctx = ContextClass()

    ctx.value = 23

    in_thread_exception = None

    def worker():
        nonlocal in_thread_exception
        try:
            with pytest.raises(AttributeError):
                assert ctx.value == 23
        except Exception as error:
            in_thread_exception = error
            raise

    t1 = threading.Thread(target=worker)
    t1.start()
    t1.join()
    assert not in_thread_exception


def test_native_context_local_interleaved_threads_context_manager():

    ctx = NativeContextLocal()

    ctx.value = 1

    in_thread_exception = None

    def worker(value1, value2, delay1=0, delay2=0):
        nonlocal in_thread_exception
        try:
            ctx.value = value1
            with ctx:
                time.sleep(delay1)
                ctx.value = value2
                time.sleep(delay2)
                assert ctx.value == value2
            assert ctx.value == value1
        except Exception as error:
            in_thread_exception = error
            raise

    assert ctx.value == 1

    t1 = threading.Thread(target=worker, args=(2, 3, 0, 0.15))
    t2 = threading.Thread(target=worker, args=(4, 5, 0.1, 0.07))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert ctx.value == 1
    assert not in_thread_exception
