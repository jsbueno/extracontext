import asyncio
import threading

from extracontext import ContextLocal, NativeContextLocal

import pytest

@pytest.mark.parametrize("CtxLocalCls", [ContextLocal, NativeContextLocal])
def test_context_local_vars_work_for_async(CtxLocalCls):

    # from types import SimpleNamespace
    ctx = CtxLocalCls()
    # ctx = SimpleNamespace() # <- uncomment to check "contextvarless" behavior.

    results = set()

    #@ctx
    async def worker(value):
        ctx.value = value
        await asyncio.sleep((10 - value) * 0.01)
        assert value == ctx.value
        results.add(ctx.value)

    #@ctx
    async def manager():
        ctx.value = -1
        tasks = asyncio.gather(*(worker(i) for i in range(10)))
        await tasks
        assert all(i in results for i in range(10))
        assert ctx.value == -1

    asyncio.run(manager())


def test_threading_local_vars_do_not_work_for_async():
    """This is an anti-test, just showing how threading local just
    do not work for async tasks:
    """

    ctx = threading.local()

    results = set()

    inner_errors = 0
    missing_values = 0

    async def worker(value):
        nonlocal inner_errors
        ctx.value = value
        await asyncio.sleep((10 - value) * 0.01)
        try:
            assert value == ctx.value
        except AssertionError:
            inner_errors += 1
        results.add(ctx.value)

    async def manager():
        nonlocal missing_values
        ctx.value = -1
        tasks = asyncio.gather(*(worker(i) for i in range(10)))
        await tasks
        missing_values = set(range(10)) - results
        assert ctx.value != -1

    asyncio.run(manager())
    assert inner_errors > 0
    assert missing_values


@pytest.mark.parametrize("CtxLocalCls", [ContextLocal, NativeContextLocal])
def test_context_local_async_reflect_changes_made_downstream(CtxLocalCls):
    """New tasks, inside "gather" call can't effect ctx as defined in manager.

    inside the same task, non-decorated co-routine affects CTX. If it were
    decorated with @ctx, it would not change the value visible in the calling "worker" co-routine.
    """


    ctx = CtxLocalCls()

    results = set()

    @ctx
    async def worker(value):
        ctx.value = value
        results.add(ctx.value)
        await isolated_second_stage_worker()
        assert ctx.value == value

        await second_stage_worker()
        assert ctx.value == value + 1

    @ctx
    async def isolated_second_stage_worker():
        await asyncio.sleep((10 - ctx.value) * 0.01)
        ctx.value += 1
        results.add(ctx.value)

    async def second_stage_worker():
        await asyncio.sleep((10 - ctx.value) * 0.01)
        ctx.value += 1
        results.add(ctx.value)

    @ctx
    async def manager():
        ctx.value = -1
        tasks = asyncio.gather(*(worker(i) for i in range(0, 10, 2)))
        await tasks
        assert all(i in results for i in range(10))
        assert ctx.value == -1

    asyncio.run(manager())
    assert all(i in results for i in range(10))


def test_nativecontext_local_works_with_tasks():
    ctx = NativeContextLocal()

    ctx.value = 5
    @ctx
    async def stage1():
        ctx.value = 23

    async def manager():
        ctx.value = 42
        task = asyncio.create_task(stage1())
        await asyncio.sleep(0.01)
        await task
        await asyncio.sleep(0.01)
        assert ctx.value == 42

    asyncio.run(manager())
    assert ctx.value == 5


@pytest.mark.parametrize("CtxLocalCls", [
    ContextLocal,
    pytest.param(NativeContextLocal, marks=pytest.mark.xfail(raises=NotImplementedError))
])
def test_context_isolates_async_loop(CtxLocalCls):

    ctx = CtxLocalCls()
    ctx.aa = 1
    results = []

    @ctx
    async def aiter():
        ctx.aa = 3
        assert ctx.aa == 3
        print(ctx.aa)
        assert ctx.aa == 3
        ctx.aa += 1
        assert ctx.aa == 4
        yield 2
        assert ctx.aa == 4

    @ctx
    async def entry():
        ctx.aa = 2
        counter = 0
        async for i in aiter():
            assert ctx.aa == 2 + counter
            ctx.aa += 10
            counter += 10

    asyncio.run(entry())
    assert ctx.aa == 1
