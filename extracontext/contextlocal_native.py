"""
Super context wrapper -

Meant to have the same interface as the easy-to-use PyContextLocal,
implemented 100% in Python, but backed by PEP 567 stdlib contextvar.ContextVar


"""

import asyncio
import inspect
import sys
import threading
import typing as ty

from contextvars import Context, ContextVar, copy_context
from functools import wraps
from types import TracebackType

from .base import ContextLocal

P = ty.ParamSpec('P')
T = ty.TypeVar('T')
T1 = ty.TypeVar('T1')
T2 = ty.TypeVar('T2')

if sys.implementation.name == "pypy":
    pypy = True
    from __pypy__ import (
        get_contextvar_context as _get_contextvar_context,
        set_contextvar_context as _set_contextvar_context,
    )

else:
    pypy = False
    try:
        import ctypes
    except ImportError as error:
        import warnings

        warnings.warn(
            f"Couldn't import ctypes! `with` context blocks for NativeContextLocal won't work:\n {error.msg}"
        )
        warnings.warn(
            "\n\nIf you need this feature in subinterpreters, please open a project issue"
        )

if sys.version_info < (3, 10):
    from types import AsyncGeneratorType

    anext = AsyncGeneratorType.__anext__

__author__ = "João S. O. Bueno"
__license__ = "LGPL v. 3.0+"

_sentinel = object()


_CtxKey = tuple[threading.Thread, None | asyncio.Task[ty.Any]]


class NativeContextLocal(ContextLocal):
    """Uses th native contextvar module in the stdlib (PEP 567)
    to provide a context-local namespace in the way
    threading.local  works for threads.

    Assignements and reading from the namespace
    should work naturally with no need to call `get` and `set` methods.

    A new contextvar variable is created in the current (contextvars) context
    for _each_ attribute acessed on this namespace.

    Also, attributes prefixed with a single "_et_" are intended for internal
    use and will not be namespaced contextvars.

    # In contrast to the pure-Python implementation there are
    # some limitations,such as the impossibility to work
    # in as a contextmanager (Python `with` block),.

    [Work In Progress]
    """

    _backend_key = "native"
    _ctypes_initialized = False

    def __init__(self, **kwargs: ty.Any):
        super().__init__(**kwargs)
        self._et_registry[str, ty.Any] = {}
        self._et_stack: dict[_CtxKey, list[tuple[Context, Context | None]]] = {}
        self._et_lock = threading.Lock()

    def __getattr__(self, name: str) -> ty.Any:
        var = self._et_registry.get(name, None)
        if var is None:
            raise AttributeError(f"Attribute not set: {name}")
        try:
            value = var.get()
        except LookupError as error:
            raise AttributeError from error
        if value is _sentinel:
            raise AttributeError(f"Attribute not set: {name}")
        return value

    def __setattr__(self, name: str, value: ty.Any) -> None:
        if name.startswith("_et_"):
            return super().__setattr__(name, value)
        var = self._et_registry.get(name, _sentinel)
        if var is _sentinel:
            var = self._et_registry[name] = ContextVar(name)
        var.set(value)

    def __delattr__(self, name: str) -> None:
        if getattr(self, name, _sentinel) is _sentinel:
            raise AttributeError(f"Attribute not set: {name}")
        setattr(self, name, _sentinel)

    def __call__(self, callable_: ty.Callable[P, T]) -> ty.Callable[P, T]:
        @wraps(callable_)
        def wrapper(*args: ty.Any, **kw: ty.Any) -> T:
            return self._run(callable_, *args, **kw)

        return wrapper

    def _ensure_api_ready(self) -> None:
        if not self._ctypes_initialized:
            ctypes.pythonapi.PyContext_Enter.argtypes = [ctypes.py_object]
            ctypes.pythonapi.PyContext_Exit.argtypes = [ctypes.py_object]
            ctypes.pythonapi.PyContext_Enter.restype = ctypes.c_int32
            ctypes.pythonapi.PyContext_Exit.restype = ctypes.c_int32
            self.__class__._ctypes_initialized = True

    def _get_ctx_key(self) -> _CtxKey:
        key_thread = threading.current_thread()
        try:
            key_task = asyncio.current_task()
        except RuntimeError:
            key_task = None
        return (key_thread, key_task)

    def _enter_ctx(self, new_ctx: Context) -> Context | None:
        if pypy:
            prev_ctx = _get_contextvar_context()
            _set_contextvar_context(new_ctx)
            return prev_ctx
        self._ensure_api_ready()
        result = ctypes.pythonapi.PyContext_Enter(new_ctx)
        if result != 0:
            raise RuntimeError(f"Something went wrong entering context {new_ctx}")
        return None

    def _exit_ctx(self, current_ctx: Context, prev_ctx: Context | None) -> None:
        if pypy:
            _set_contextvar_context(ty.cast(Context, prev_ctx))
            return
        result = ctypes.pythonapi.PyContext_Exit(current_ctx)
        if result != 0:
            raise RuntimeError(f"Something went wrong exiting context {current_ctx}")

    def __enter__(self) -> ty.Self:
        new_ctx = copy_context()
        prev_ctx = self._enter_ctx(new_ctx)
        with self._et_lock:
            self._et_stack.setdefault(self._get_ctx_key(), []).append(
                (new_ctx, prev_ctx)
            )
        return self

    def __exit__(self, exc_type: type[BaseException], exc_value: BaseException, traceback: TracebackType) -> None:
        key = self._get_ctx_key()
        with self._et_lock:
            current_ctx, prev_ctx = self._et_stack[key].pop()
            if not self._et_stack[key]:
                self._et_stack.pop(key)
        self._exit_ctx(current_ctx, prev_ctx)

    def _run(self, callable_: ty.Callable[P, T], *args: ty.Any, **kw: ty.Any) -> T:
        """Runs callable with an isolated context
        no need to decorate the target callable
        """
        new_context = copy_context()
        result: T | ty.Awaitable[ty.Any] | ty.Generator[ty.Any, ty.Any, ty.Any] | ty.AsyncGenerator[ty.Any] = new_context.run(callable_, *args, **kw)
        if inspect.isawaitable(result):
            result = self._awaitable_wrapper(result, new_context)
        elif inspect.isgenerator(result):
            result = self._generator_wrapper(result, new_context)
        elif inspect.isasyncgen(result):
            result = self._async_generator_wrapper(result, new_context)
        return ty.cast(T, result)

    @staticmethod
    def _generator_wrapper(generator: ty.Generator[T, T1, T2], ctx_copy: Context) -> ty.Generator[T, T1, T2]:
        value: None | T | T1 = None
        while True:
            try:
                if value is None:
                    value = yield ctx_copy.run(next, generator)
                else:
                    value = yield ctx_copy.run(generator.send, ty.cast(T1, value))
            except StopIteration as stop:
                return ty.cast(T2, stop.value)
            except GeneratorExit:
                ctx_copy.run(generator.close)
                raise
            except Exception as exc:
                # for debugging times: this will be hard without a break here!
                # print(exc)
                try:
                    value = ctx_copy.run(generator.throw, exc)
                except StopIteration as stop:
                    return ty.cast(T2, stop.value)


    async def _awaitable_wrapper(self, coro: ty.Coroutine[ty.Any, ty.Any, T], ctx_copy: Context) -> ty.Coroutine[ty.Any, ty.Any, T]:
        def trampoline() -> asyncio.Task[T]:
            return asyncio.create_task(coro, context=ctx_copy)

        return await ctx_copy.run(trampoline)

    if sys.version_info < (3, 11):
        # Older Pythons don't have a "context" argument to `create_task`
        async def _awaitable_wrapper(self, coro, ctx_copy):
            from ._future_task import FutureTask

            loop = asyncio.get_running_loop()

            def trampoline():
                return FutureTask(coro, loop=loop, context=ctx_copy)

            return await ctx_copy.run(trampoline)

        ## this fails in spetacular and inovative ways!
        # async def _awaitable_wrapper(self, coro, ctx_copy, force_context=True):
        # if force_context:
        # try:
        # self._enter_ctx(ctx_copy)
        # result = await coro
        # finally:
        # self._exit_ctx(ctx_copy)
        # return result
        # else:
        # return await coro

        async def _awaitable_wrapper2(self, coro, ctx_copy):
            raise NotImplementedError(
                """This code will only work with Python versions > 3.11. Please use `ContextLocal(backend="python")` for Python version 3.8 - 3.10"""
            )

    async def _async_generator_wrapper(self, generator, ctx_copy):
        value = None
        while True:
            try:
                if value is None:
                    async_res = ctx_copy.run(anext, generator)
                else:
                    async_res = ctx_copy.run(generator.asend, value)
                value = yield await self._awaitable_wrapper(async_res, ctx_copy)
            except GeneratorExit:
                async_res = ctx_copy.run(generator.aclose)
                await self._awaitable_wrapper(async_res, ctx_copy)
                raise
            except StopAsyncIteration:
                break
            except Exception as exc:
                # for debugging times: this will be hard without a break here!
                # print("*" * 50 , exc)
                try:
                    async_res = ctx_copy.run(generator.athrow, exc)
                    value = yield await self._awaitable_wrapper(async_res, ctx_copy)
                except StopAsyncIteration:
                    break

    def __dir__(self):
        return list(
            key
            for key, value in self._et_registry.items()
            if value.get() is not _sentinel
        )
