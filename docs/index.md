# extracontext

**Context Variable namespaces supporting generators, asyncio and multi-threading.**

`extracontext` provides utilities and facilities to isolated context variables added to Python 3.7, including an isolated namespace, no need to manually calling getters and setters, straightforward function calling and context managers. 

In other words, it provides a [PEP 567](https://peps.python.org/pep-0567/)-compliant, drop-in replacement for `threading.local` namespaces that also works seamlessly with asyncio tasks and generators.

## Why extracontext?

Python's built-in `contextvars` module requires verbose boilerplate: each variable must be declared at the top level, and `.get()`/`.set()` methods must be used explicitly. Isolating a function from leaking context changes requires the caller to use `Context.run()`.

`extracontext` restores the simplicity of attribute access and `=` assignment, while providing the same concurrency safety:

```python
# stdlib contextvars — verbose
import contextvars
ctx_color = contextvars.ContextVar("ctx_color")
ctx_color.set("red")
print(ctx_color.get())
```

```python
# extracontext — simple
from extracontext import ContextLocal
ctx = ContextLocal()
ctx.color = "red"
print(ctx.color)
```

Context isolation is declared on the callee, not the caller:

```python
from extracontext import ContextLocal

ctx = ContextLocal()

@ctx
def render_markup(text):
    # Changes here never leak back to the caller
    ctx.color = "blue"
    ...

ctx.color = "red"
render_markup(my_text)
assert ctx.color == "red"  # unchanged
```

## Installation

```
pip install python-extracontext
```

## Quick Start

```python
from extracontext import ContextLocal

ctx = ContextLocal()

@ctx
def worker(value):
    ctx.result = value * 2
    return ctx.result

ctx.result = 0
worker(21)
assert ctx.result == 0  # not affected by the isolated call
```

See the [Usage Guide](usage.md) for more examples, or the [API Reference](api.md) for the full public API.
