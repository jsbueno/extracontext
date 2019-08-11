import asyncio

from extracontext import ContextLocal


def test_context_local_vars_work_for_async():


    ctx = ContextLocal()

    results = set()

    @ctx.context
    async def worker(value):
        ctx.value = value
        asyncio.sleep((10 - value) * 0.01)
        assert value == ctx.value
        results.add(ctx.value)

    @ctx.context
    def manager():
        ctx.value = -1
        tasks = asyncio.gather(*(worker(i) for i in range(10)))
        loop = asyncio.get_event_loop()
        loop.run_until_complete(tasks)
        print(results)
        assert all(i in results for i in range(10))
        assert ctx.value == -1

    manager()
