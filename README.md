# Extracontext: Context Local Variables for everyone

## Description

Provides [PEP 567](https://peps.python.org/pep-0567/)
compliant drop-in replacement for `threading.local`
namespaces.

The main goal of PEP 567, supersedding [PEP 550](https://peps.python.org/pep-0550/)
is to create a way to preserve information in
concurrent running contexts, including multithreading
and asynchronous (asyncio) tasks, allowing
each call stack to have its own versions of
variables containing settings, or request
parameters.

### Quoting from PEP 567 Rationalle:
> Thread-local variables are insufficient for asynchronous
> tasks that execute concurrently in the same OS thread.
> Any context manager that saves and restores a context
> value using threading.local() will have its context values
> bleed to other code unexpectedly when used in async/await code.

## Rationale for "extracontext"

Contextcars, introduced in Python 3.7, were
implemented following a design decision by the
which opted-out of the namespace approach
used by Python's own `threading.local`
implementation. It then requires an explicit top level
declaration of each context-local variable, and
the (rather "unpythonic") usage of an explicit
call to `get` and `set` methods to manipulate
those. Also, the only way to run some code in
an isolated context copy is to call a function
indirectly through means of the context object  `.run` method.
This implies that:

1. Knowing when to run something in a different context is responsability of the caller code
2. Breaks the easy-to-use, easy-to-read, aesthetics, and overal complicates one of the most fundamental blocks of programming in inperative languages: calling functions.

This package does away with that, and brings simplicity
back, using dotted attributes to a namespace and `=`
for value assigment:

with stdlib native contexvars:

```python
import contextvars

# Variable declaration: top level declaration and WET (write everything twice)
ctx_color = contextvars.ContextVar("ctx_color")
ctx_font = contextvars.ContextVar("ctx_font")

def blah():
    ...
    # use  a set method:
    ctx_color.set("red")
    ctx_font.set("arial")

    ...
    myttext = ...
    # call a markup render function,
    # but take care it wont mix our attributes in temporary context changes
    contextvars.context_copy().run(render_markup, mytext))
    ...

def render_markup(text):
    # markup function: knows it will mess up the context, but can't do
    # a thing about it - the caller has to take care!
    ...
```

with extracontext:

```python
import extracontext

# the only declaration needed at top level code
ctx = extracontext.ContextLocal()

def blah():
    ctx.color = "red"
    ctx.font = "arial"

    mytext = ...
    # simply calls  the function
    render_markup(mytext)
    ...

@ctx
def render_markup(text):
    # we will mess the context - but the decorator
    # ensures no changes leak back to the caller
    ...

```

## Usage
simply instantiate a `ContextLocal` namespace,
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

## More Features:

### extracontext namespaces work for generators

Unlike PEP 567 contextvars, extracontext
will sucessfully isolate contexts whe used with
generator-functions - meaning,
the generator body is actually executed in
an isolated context:

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

This is virtually impossible with contextvars.  (Ok,
not impossible - the default extracontext backend
does that using contextvars after all - but it encapsulates
the complications for you)

This feature also works with async generators`


Another example of this feature:

```python
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


### Change context within  a context-manager `with` block:

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


### Map namespaces

Beyond namespace usages, `extracontext` offer ways
to have contexts working as mutable mappings,
using the `ContextMap` class.


```python

from extracontext import ContextMap

# global namespace, available in any thread or async task:
ctx = ContextMap()

def myworker():
    # value set only visible in the current thread or asyncio task:
    ctx["value"] = "test"


```


### New for 1.0

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
