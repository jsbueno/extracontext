Context Local Variables
==========================

Implements a Pythonic way to work with PEP 567
contextvars (https://peps.python.org/pep-0567/ )

Introduced in Python 3.7, a design decision by the
authors of the feature decided to opt-out of
the simple namespace used by Python's own `threading.local`
implementation, and requires an explicit top level
declaration of each context-local variable, and
the (rather "unpythonic") usage of an explicit
call to `get` and `set` methods to manipulate
those.

This package does away with that, and brings simplicity
back - simply instantiate a `ContextLocal` namespace,
and any attributes set in that namespace will be unique
per thread and per asynchronous call chain (i.e.
unique for each independent task).

In a sense, these are a drop-in replacement for
`threading.local`, which will also work for
asynchronous programming without any change in code.

One should just avoid creating the "ContextLocal" instance itself
in a non-setup function or method - as the implementation
uses Python contextvars in by default, those are not
cleaned-up along with the local scope where they are
created - check the docs on the contextvar module for more
details.

However, creating the actual variables to use inside this namespace
can be made local to functions or methods: the same inner
ContextVar instance will be re-used when re-entering the function


Usage:

Create one or more project-wide instances of "extracontext.ContextLocal"
Decorate your functions, co-routines, worker-methods and generators
that should hold their own states with that instance itself, using it as a decorator

and use the instance as namespace for private variables that will be local
and non-local until entering another callable decorated
with the instance itself - that will create a new, separated scope
visible inside  the decorated callable.

```python

from extracontext import ContextLocal

# global namespace, available in any thread or async task:
ctx = ContextLocal()

def myworker():
    # value set only visible in the current thread or asyncio task:
    ctx.value = "test"


```

More Features:

Unlike `threading.local` namespaces, one can explicitly isolate a contextlocal namespace
when calling a function even on the same thread or same async call chain (task). And unlike
`contextvars.ContextVar`, there is no need to have an explicit context copy
and often an intermediate function call to switch context: `extracontext.ContextLocal`
can isolate the context using either a `with` block or as a decorator
(when entering the decorated function, all variables in the namespace are automatically
protected against any changes that would be visible when that call returns,
the previous values being restored).


Example showing context separation for concurrent generators:



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

Map namespaces
-----------------

The `ContextMap` class works just the same way, but works
as a mapping:


```python

from extracontext import ContextMap

# global namespace, available in any thread or async task:
ctx = ContextMap()

def myworker():
    # value set only visible in the current thread or asyncio task:
    ctx["value"] = "test"


```

Non Leaky Contexts
-------------------
Contrary to default contextvars usage, generators
(and async generators) running in another context do
take effect inside the generator, and doesn't
leak back to the calling scope:

```
import extracontext
ctx = extracontext.ContextLocal()
@ctx
def isolatedgen(n):
    for i in range(n):
        ctx.myvar = i
        yield i
        print (ctx.myvar)
def test():
    ctx.myvar = "lambs"
    for j in isolatedgen(2):
        print(ctx.myvar)
        ctx.myvar = "wolves"

In [11]: test()
lambs
0
wolves
1
```

By using a stdlib `contextvars.ContextVar` one simply
can't isolate the body of a generator, save by
not running a `for` at all, and running all
iterations manually by calling `ctx_copy.run(next, mygenerator)`



New for 1.0
-----------

Switch the backend to use native Python contextvars (exposed in
the stdlib "contextvars" module by default.

Up to the update in July/Aug 2024 the core package functionality
was provided by a pure Python implementation which keeps context state
in a hidden frame-local variables - while that is throughfully tested
it performs a linear lookup in all the callchain for the context namespace.

 For the 0.3 release, the "native" stdlib contextvars.ContextVar backed class,
 has reached first class status, and is now the default method used.

 The extracontext.NativeContextLocal class builds on Python's contextvars
 instead of reimplementing all the functionality from scratch, and makes
 simple namespaces and decorator-based scope isolation just work, with
 all the safety and performance of the Python native implementation,
 with none of the boilerplate or confuse API.


Next Steps:
-----------
(not so sure about these - they are fruit of some 2018 brainstorming for
features in a project I am not coding for anymore)


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
