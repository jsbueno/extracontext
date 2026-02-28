# Usage Guide

## Basic Usage

Instantiate a `ContextLocal` namespace once (typically at module level). Any attribute set on it is visible only within the current thread or asyncio task:

```python
from extracontext import ContextLocal

ctx = ContextLocal()

def myworker():
    ctx.value = "test"  # only visible in this thread/task
```

## Decorator: Isolated Function Scope

Decorate a function with the `ContextLocal` instance to execute it in an isolated copy of the context. Changes made inside the function are never visible to the caller:

```python
from extracontext import ContextLocal

ctx = ContextLocal()

@ctx
def isolated_example():
    ctx.value = 2
    assert ctx.value == 2

ctx.value = 1
isolated_example()
assert ctx.value == 1  # unchanged
```

The decorator works for plain functions, generator functions, coroutine functions, and async generator functions.

## Context Manager: Isolated `with` Block

Use the `ContextLocal` instance as a context manager to isolate changes within a `with` block:

```python
from extracontext import ContextLocal

ctx = ContextLocal()
ctx.value = 1

with ctx:
    ctx.value = 2
    assert ctx.value == 2

assert ctx.value == 1  # restored
```

Context managers are re-entrant, so nested `with ctx:` blocks work correctly.

## Generator Isolation

Unlike stdlib `contextvars`, `extracontext` properly isolates context for each generator instance across `yield` points:

```python
from extracontext import ContextLocal

ctx = ContextLocal()
results = []

@ctx
def contexted_generator(value):
    ctx.value = value
    yield
    results.append(ctx.value)

generators = [contexted_generator(i) for i in range(10)]
any(next(gen) for gen in generators)
any(next(gen, None) for gen in generators)

assert results == list(range(10))  # each generator kept its own value
```

This also works with async generators.

## Asyncio Support

`ContextLocal` instances work transparently with asyncio tasks — each task sees its own isolated copy of the context:

```python
import asyncio
from extracontext import ContextLocal

ctx = ContextLocal()

async def task(value):
    ctx.value = value
    await asyncio.sleep(0)
    assert ctx.value == value  # other tasks don't interfere

async def main():
    await asyncio.gather(*[task(i) for i in range(10)])

asyncio.run(main())
```

## ContextMap: Dictionary-Style Access

`ContextMap` is a `ContextLocal` subclass implementing `collections.abc.MutableMapping`. It supports both `ctx["key"]` and `ctx.key` access:

```python
from extracontext import ContextMap

ctx = ContextMap()

def myworker():
    ctx["value"] = "test"
    assert ctx.value == "test"  # attribute access also works
```

Optionally initialize with an existing mapping:

```python
ctx = ContextMap({"color": "red", "font": "arial"})
```

All standard mapping methods are available: `keys()`, `values()`, `items()`, `get()`, `pop()`, `clear()`, `update()`, `setdefault()`.

## Cross-Thread Context Preservation

When using `asyncio` with a thread pool executor, context normally doesn't propagate to the worker thread. `ContextPreservingExecutor` fixes this:

```python
import asyncio
import random
import time
from extracontext import ContextLocal, ContextPreservingExecutor

ctx = ContextLocal()

def sync_part():
    time.sleep(random.random())
    print(ctx.value)  # sees the calling task's context

async def async_task(executor, value):
    ctx.value = value
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(executor, sync_part)

async def main():
    with ContextPreservingExecutor() as executor:
        async with asyncio.TaskGroup() as tg:
            for value in range(10):
                tg.create_task(async_task(executor, value))

asyncio.run(main())
```

Each thread call sees the context of its originating asyncio task.

> **Note:** `ContextPreservingExecutor` requires the default `"native"` backend. The pure Python backend does not support shared values across threads.

## Choosing a Backend

By default, `ContextLocal` uses the `"native"` backend (based on stdlib `contextvars`). You can explicitly select the pure-Python backend:

```python
ctx = ContextLocal(backend="python")   # pure Python reimplementation
ctx = ContextLocal(backend="native")   # stdlib contextvars (default)
```

The native backend is recommended for all production use. The Python backend is useful for debugging or environments where native contextvars have issues.
