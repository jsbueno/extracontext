import gc
import sys
from collections.abc import Mapping, Sequence
from contextlib import contextmanager

import pytest

from extracontext import ContextLocal, ContextError


def test_context_local_vars_work_as_namespace():
    ctx = ContextLocal()
    ctx.value = 1
    assert ctx.value == 1
    del ctx.value
    with pytest.raises(AttributeError):
        assert ctx.value == 1


def test_each_call_creates_unique_context_and_clean_up():
    context_keys = set()

    ctx = ContextLocal()

    @ctx.context
    def testcall():
        context_keys.update(ctx._registry.keys())

    for i in range(10):
        testcall()

    assert len(context_keys) == 10
    assert len(list(ctx._registry.keys())) == 0


def test_unique_context_for_generators_is_cleaned_up():
    context_keys = set()

    ctx = ContextLocal()

    @ctx.context
    def testcall():
        context_keys.update(k.value for k in ctx._registry.keys())
        yield None

    for i in range(100):
        for _ in testcall():
            pass
    gc.collect()


    assert len(context_keys) == 100
    assert len(list(ctx._registry.keys())) == 0


def recursive_size(obj):
    size = sys.getsizeof(obj)
    if isinstance(obj, Mapping):
        for key, value in obj.items:
            size += recursive_size(key)
            size += recursive_size(value)
    elif isinstance(obj, Sequence):
        for item in obj:
            size += recursive_size(item)
    elif hasattr(obj, "__dict__"):
        size += recursive_size(obj.__dict__)
    return size



#def test_abusive_memory_leak():
    #ctx = ContextLocal()

    #@ctx.context
    #def func(n):



