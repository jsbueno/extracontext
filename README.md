Context Local Variables
==========================


Context Local Variables meant to enable
separate variable values for code running either
in asyncio, using generators, or multiple-threads.


These are meant to be simpler to use and work in more scenarios than
Python's contextvars.

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
