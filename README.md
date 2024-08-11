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

### typing support
There is no explicit typing support yet - but note that through the use of
`ContextMap` it is possible to have declare some types, by
simple declaring `Mapping[type1:type2]` typing.


## Specification and Implementation

### ContextLocal

`ContextLocal`  is the main class, and should suffice for most uses.
It only takes the `backend` keyword-only argument,  which selects
the usage of the pure-Python backend (`"python"`) or using
a contextvars.ContextVar backend (`"native"`). The later is the default
behavior. Calling this class will actually create
an instance of the appropriate subclass, according to
the backend: either `PyContextLocal` or `NativeContextLocal` -
 in the same way stdlib `pathlib.Path` creates
an instance of Path appropriate for Posix, or Windows style
paths. (This pattern probably have a name - help welcome).

An instance of it will create a new, fresh, namespace.
Use dotted attribute access to populate it - each variable set
in this way will persist through the context lifetime.

#### Usage as a decorator:
When used as a decorator for a function or method, that callable
will automatically be executed in a copy of the calling context -
meaning no changes it makes to any variable in the namespace
is visible outside of the call.

The decorator (and the isolation provided) works for
both plain functions, generator functions, co-routine functions
and async generator functions - meaning that whenever the
execution switches to the caller context
(in `yield` or `await` expression) the context is
restored to that of the caller, and when it
re-enters the paused code block, the isolated
context is restored.


```python
from extracontext import ContextLocal

ctx = ContextLocal()

@ctx
def isolated_example():

    ctx.value = 2
    assert ctx.value = 2

ctx.value = 1
isolated_example()
assert ctx.value == 1

```

#### Usage as a context manager

A `ContextLocal` instance can simply be used in a
context manager `with` statement, and any variables
set or changed within the block will not be
persisted after the block is over.

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

Also, they are re-entrant, so if in a function called
within the block, the context is used again
as a context manager, it will just work.


#### Semantic difference to contextvars.ContextVar
   Note that a fresh `ContextLocal()` instance will
be empty, and have access to none of the values _or names_
set in another instance. This contrasts sharply with
`contextvars.Context`, for which each `contextvars.ContextVar`
created anywhere else in the program (even 3rd party
modules) is a valid key.


### PyContextLocal
ContextLocal implementation using pure Python code, and
reimplementing the functionalities of Contexts and ContextVars
as implemented by PEP 567 fro scratch.

It works by seeting, in a "hidden" way, values in the caller's
closure (the `locals()` namespace). Though writting
to this namespace has traditionally been a "grey area"
in  Python, the way it makes use of this data is compliant
with the specs in [PEP-558](https://peps.python.org/pep-0558/)
which officializes this use for Python 3.13 and beyond
(and it has always worked since Python 3.0.
The first implementations of this code where
tested against Python 3.4 and forward)

It should be kept in place for the time being,
and could be useful to allow customizations,
workarounds, or buggy behavior bypassing
where the native implementation presents
any short-commings.

It is not an easy to follow code, as in
one hand there are introspection and meta-programming
patterns to handle access to the data in a containirized way.

Keep in mind that native contexvars use an
internal copy-on-write structure in  native code
which should be much more performant than
the chain-mapping checks used in this backend.


It has been throughfully tested and should be bug free,
though less performant.

### NativeContextLocal

This leverages on PEP 567 Contexts and ContextVars
to perform all the isolation and setting mechanics,
and provides an convenient wrapper layer
which works as a namespace (and as mapping in NativeContextMap)

It was made the default mechanism due to obvious
performances and updates taking place in the
embedded implementation in the language.

The normal ContextVarsAPI exposed to Python
would not allow for changing context inside the
same function, requiring a `Context.run` call
as the only way to switch contexts. Instead of releasing this
backend without this mechanism, it has been opted
to call the native cAPI for changing
context (using `ctypes` in cPython, and the relevant internal
calls on pypy) so that the feature can work.

When this feature was implemented, `NativeContextLocal`
instances could then work as a context-manager using
the `with` statement, and there were no reasons why
they should not be the default backend. Some
coding effort were placed in the "Reverse subclass picking"
mechanism, and it was made te default in a backwards-
compatible way.

### ContextMap

`ContextMap` is a `ContextLocal` subclass which implements
[the `MutableMapping` interface](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping).
It is pretty straightforward in
that, so that assigments and retrievals using the `ctx["key"]`
syntax are made available, functionality with the
`in`, `==`, `!=` operators and the `keys`, `items`, `values`, `get`, `pop`, `popitem`, `clear`, `update`, and `setdefault` methods.

It supports loadding a mapping with the initial context contents, passed as
the `initial` positional argument - but not keyword-args mapping to initial
content (as in `dict(a=1)`).

Also, it is a subclass of ContextLocal - so it also allows access to the
keys with the dotted attribute syntax:

```python

a = extracontext.ContextMap

a["b"] = 1

assert a.b == 1

```

And finally, it uses the same `backend` keyword-arg mechanism to switch between the default
native-context vars backend and the pure Python backend, which will yield either
a `PyContextMap` or a `NativeContextMap` instance, accordingly.

### PyContextMap
`ContextMap` implementation as a subclass of `PyContextLocal`

### NativeContextMap
`ContextMap` implementation as a subclass of `NativeContextLocal`



### History
The original implementation from 2019 re-creates
all the functionality provided by the PEP 567
contextvars using pure Python code and a lot
of introspection and meta-programming.
Not sure why it did that - but one thing is that
it coud provide the functionality for older
Pythons at the time, and possibly also because
I did not see, at the time, other ways
to workaround the need to call a function
in order to switch contexts.

At some revival sprint in 2021, a backend
using native contextvars was created -
and it just got to completion,
with all features and tests for the edge clases in
August 2024, after other periods of non-activity.

At this point, a mechanism for picking the
desired backend was implemented, and the native
`ContextLocal` class was switched to use the
native stdlib contextvars as backend by default.
(This should be much faster - benchmark
contributions are welcome, though :-)  )


## New for 1.0

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


## Next Steps

1. Implementing more of the features possible with the contextvars semantics
  - `.run` and `.copy` methods
  - direct access to "`Token`"s as used by contextvars
  - default value setting for variables

1. A feature allowing other threads to start from a copy of the current context, instead of an empty context. (asyncio independent tasks always see a copy)

1. Bringing in some more typing support
(not sure what will be possible, but I believe some
`typing.Protocol` templates at least. On an
initial search, typing for namespaces is not
a widelly known feature (if at all)

1. (maybe?) Proper multiprocessing support:
  - ironing out probable serialization issues,
  - allowing subprocess workers to start from a copy of the current context.

1. (maybe?) support for nested namespaces and maps.

### Old "Next Steps":
-----------
(not so sure about these - they are fruit of some 2019 brainstorming for
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

 1. Shared values and locks: values that are guarranteed to be the same across tasks/threads, and a lock mechanism allowing atomic operations with these values.
