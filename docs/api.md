# API Reference

All public objects are importable from the top-level `extracontext` package.

## ContextLocal

The main entry point. A factory that returns either a `NativeContextLocal` or `PyContextLocal` instance depending on the `backend` argument.

::: extracontext.ContextLocal

---

## ContextMap

A `ContextLocal` subclass implementing `collections.abc.MutableMapping`, providing dictionary-style access alongside attribute access.

::: extracontext.ContextMap

---

## ContextPreservingExecutor

A `concurrent.futures.ThreadPoolExecutor` subclass that propagates the current context into worker threads.

::: extracontext.ContextPreservingExecutor

---

## ContextError

Exception raised when a context variable is accessed outside a valid scope.

::: extracontext.ContextError

---

## NativeContextLocal

The default backend implementation, built on stdlib `contextvars.ContextVar`.

::: extracontext.NativeContextLocal

---

## PyContextLocal

The pure-Python backend implementation, using frame introspection.

::: extracontext.PyContextLocal
