import asyncio
import threading
import time
from collections import deque

from contextvars import ContextVar, copy_context

import pytest

from extracontext import ContextPreservingExecutor




def test_executor_preserves_context():
    # test executed using ordinary contexts

    ctx = ContextPreservingExecutor(1)

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
        task1 = loop.run_in_executor(ctx, stage_3)
        task2 = asyncio.sleep(0.05)
        await asyncio.gather(task1, task2)
        if all_ok:
            all_ok = myvar.get() == 23
            if not all_ok:
                message = "Context var not reset to in-task value after thread call"

    def stage_3():
        nonlocal all_ok, message
        all_ok = (x:=myvar.get() == 23)
        if not all_ok:
            message = f"Context var set to {myvar.get()} in thread worker. Expecting 23!"
        myvar.set(42)


    copy_context().run(stage_1)

    assert all_ok, message
