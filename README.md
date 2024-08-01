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



This is what one has to do if "isolated_function" will use a contextvar value
for other nested calls, but should not change the caller's visible value:

```python
##########################
# using stdlib contextvars:

import contextvars

# Each variable has to be declared at top-level:
value = contextvars.ContextVar("value")

def parent():
    # explicit use of setter method for each value:
    value.set(5)
    # call to nested function which needs and isolated copy of context
    # must be done in two stages:
    new_context = contextvars.copy_context()
    new_context.run(isolated_function)
    # explicit use of getter method:
    assert value.get() == 5

def isolated_function()
    value.set(23)
    # run other code that needs "23"
    # ...
    assert value.get(23)


```

This is the same code using this package:
```python
from extracontext import NativeContextLocal

# instantiate a namespace at top level:
ctx = NativeContextLocal()

def parent():
    # create variables in the namespace without prior declaration:
    # and just use the assignment operator (=)
    ctx.value = 5
    # no boilerplate to call function:
    isolated_function()
    # no need to call a getter:
    assert ctx.value == 5

# Decorate function that should run in an isolated context:
@ctx
def isolated_function()
    assert ctx.value == 5
    ctx.value = 23
    # run other code that needs "23"
    # ...
    assert ctx.value == 23

```
In (advanced) Progress:
-----------

 A "native" stdlib contextvars.ContextVar backed class, and add some
 performance benchmarking. Current implementation is Python code
 all the way and "hides" context values in the frame local variables.

 The extracontext.NativeContextLocal class builds on Python's contextvars
 instead of reimplementing all the functionality from scratch, and makes
 simple namespaces and decorator-based scope isolation just work, with
 all the safety and performance of the Python native implementation,
 with none of the boilerplate or confuse API.
 (Isolation inside a function in a `with` statement block is not possible, though

  Progress for the native implementation is advanced, and once it is passing the
  tests, it will probably become the default class for the package. (and at this point
  we should make a stable release)


Next Steps:
-----------

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
