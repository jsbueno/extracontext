import asyncio

from extracontext import ContextLocal


def test_context_local_vars_work_for_async():


    ctx = ContextLocal()

    results = set()

    @ctx.context
    async def worker(value):
        ctx.value = value
        await asyncio.sleep((10 - value) * 0.01)
        assert value == ctx.value
        results.add(ctx.value)

    @ctx.context
    def manager():
        ctx.value = -1
        tasks = asyncio.gather(*(worker(i) for i in range(10)))
        loop = asyncio.get_event_loop()
        loop.run_until_complete(tasks)
        assert all(i in results for i in range(10))
        assert ctx.value == -1

    manager()



def test_context_local_async_reflect_changes_made_downstream():


    ctx = ContextLocal()

    results = set()

    @ctx.context
    async def worker(value):
        ctx.value = value
        results.add(ctx.value)
        await second_stage_worker()
        assert ctx.value == value + 1

    async def second_stage_worker():
        await asyncio.sleep((10 - ctx.value) * 0.01)
        ctx.value += 1
        results.add(ctx.value)

    @ctx.context
    def manager():
        ctx.value = -1
        tasks = asyncio.gather(*(worker(i) for i in range(0, 10, 2)))
        loop = asyncio.get_event_loop()
        loop.run_until_complete(tasks)
        assert all(i in results for i in range(10))
        assert ctx.value == -1

    manager()
