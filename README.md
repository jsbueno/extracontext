Context Local Variables
==========================


Context Local Variables meant to enable
separate variable values for code running either
in asyncio, using generators, or multiple-threads.


These are meant to be simpler to use and work in more scenarios than
Python's contextvars.(PEP 567)

Usage:

Create one or more project-wide instances of "extracontext.ContextLocal"
Decorate your functions, co-routines, worker-methods and generators
that should hold their own states with that instance itself, using it as a decorator

and use the instance as namespace for private variables that will be local
and non-local until entering another callable decorated
with the instance itself - that will create a new, separated scope
visible inside  the decorated callable.


Example:



```python
from extracontext import ContextLocal


ctx = ContextLocal()

results = []
@ctx
def contexted_generator(value):
    ctx.value = value
    yield None
    results.append(ctx.value)



def runner():
    generators = [contexted_generator(i) for i in range(10)]
    any(next(gen) for gen in generators)
    any(next(gen, None) for gen in generators)
    assert results == list(range(10))
```

ContextLocal namespaces can also be isolated by context-manager blocks (`with` statement):

```python
from extracontext import ContextLocal


def with_block_example():

    ctx = ContextLocal()
    ctx.value = 1
    with ctx:
        ctx.value = 2
        assert ctx.value == 2

    assert ctx.value == 1


```
In Progress:
-----------

 1. A "native" contextvars.ContextVar backed class, and add some
 performance benchmarking. Current implementation is Python code
 all the way and "hides" context values in the frame local variables.


Next Steps:
-----------

 1. Automatically enter a new inner-scope in each function call:
     no need to worry about decorators, context-managers or whatever to keep
     the higher-level values safe.

 1. Add a way to chain-contexts, so, for example
and app can have a root context with default values

 1. Describe the capabilities of each Context class clearly in a data-scheme,
 so one gets to know, and how to retrieve classes that can behave like maps, or
 allow/hide outter context values, work as a full stack, support the context protocol (`with` command),
 etc... (this is more pressing since stlib contextvar backed Context classes will
         not allow for some of the capabilities in the pure-Python reimplementation in "ContextLocal")

 1. Add a way to merge wrappers for different ContextLocal instances on the same function

 1. Add an "auto" flag - all called functions/generators/co-routines create a child context by default.

 1. Add support for a descriptor-like variable slot - so that values can trigger code when set or retrieved

 1. Shared values and locks: values that are guarranteed to be the same across tasks/threads, and a lock mechanism allowing atomic operations with these values. (extra bonus: try to develop a deadlock-proof lock)
