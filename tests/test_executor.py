import asyncio

from contextvars import ContextVar, copy_context

# import pytest

from extracontext import ContextPreservingExecutor, ContextLocal


def test_executor_preserves_context():
    # test executed using ordinary contexts
    executor = ContextPreservingExecutor(1)

    myvar = None

    all_ok, message = False, ""

    def stage_1():
        nonlocal myvar
        myvar = ContextVar("myvar", default=5)
        asyncio.run(stage_2())
        # assert myvar.get() == 5  # defautl contextvar behavior!

    async def stage_2():
        nonlocal all_ok, message  # myvar
        myvar.set(23)
        loop = asyncio.get_running_loop()
        task1 = loop.run_in_executor(executor, stage_3)
        task2 = asyncio.sleep(0.05)
        await asyncio.gather(task1, task2)
        if all_ok:
            all_ok = myvar.get() == 23
            if not all_ok:
                message = "Context var not reset to in-task value after thread call"

    def stage_3():
        nonlocal all_ok, message
        all_ok = myvar.get() == 23
        if not all_ok:
            message = (
                f"Context var set to {myvar.get()} in thread worker. Expecting 23!"
            )
        myvar.set(42)

    copy_context().run(stage_1)

    assert all_ok, message


def test_executor_preserves_context_context_locals():
    # Using ContextLocal()

    executor = ContextPreservingExecutor(1)

    ctx = ContextLocal()
    ctx.value = 5

    all_ok, message = False, ""

    def stage_1():
        asyncio.run(stage_2())

    async def stage_2():
        nonlocal all_ok, message  # myvar

        ctx.value = 23
        loop = asyncio.get_running_loop()
        task1 = loop.run_in_executor(executor, stage_3)
        task2 = asyncio.sleep(0.05)
        await asyncio.gather(task1, task2)
        if all_ok:
            all_ok = ctx.value == 23
            if not all_ok:
                message = "Context var not reset to in-task value after thread call"

    def stage_3():
        nonlocal all_ok, message
        all_ok = ctx.value == 23
        if not all_ok:
            message = f"Context var set to {ctx.value} in thread worker. Expecting 23!"
        ctx.value = 42

    copy_context().run(stage_1)

    assert all_ok, message


def test_executor_preserves_context_across_several_tasks():
    num_tasks = 100

    executor = ContextPreservingExecutor(1)

    ctx = ContextLocal()
    ctx.value = 5

    all_ok, message = True, ""

    def stage_1():
        asyncio.run(stage_2())

    async def stage_2():
        nonlocal all_ok, message  # myvar

        ctx.value = 255

        tasks = [asyncio.create_task(stage_3(i)) for i in range(num_tasks)]
        await asyncio.gather(*tasks)

        if all_ok:
            all_ok = ctx.value == 255
            if not all_ok:
                message = "Context var not reset to in-task value after thread call"

    async def stage_3(value):
        ctx.value = value

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(executor, stage_4, value)

    def stage_4(value):
        nonlocal all_ok, message
        this_ok = ctx.value == value
        if not this_ok:
            message += (
                f"Context var set to {ctx.value} in thread worker. Expected {value}!\n"
            )
            all_ok = False
        ctx.value = 512

    copy_context().run(stage_1)

    assert all_ok, message
