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


def test_context_function_holds_unique_value_for_attribute():
    context_keys = set()

    ctx = ContextLocal()

    @ctx.context
    def testcall():
        assert ctx.var1 == 1
        ctx.var1 = 2
        assert ctx.var1 == 2
        del ctx.var1


    ctx.var1 = 1
    assert ctx.var1 == 1
    testcall()
    assert ctx.var1 == 1


def test_context_inner_function_cant_erase_outter_value():
    context_keys = set()

    ctx = ContextLocal()

    @ctx.context
    def testcall():
        ctx.var1 = 2
        assert ctx.var1 == 2
        del ctx.var1

    ctx.var1 = 1
    testcall()
    assert ctx.var1 == 1


def test_context_inner_function_trying_to_erase_outter_value_blocks_cant_read_attribute_back():
    context_keys = set()

    ctx = ContextLocal()

    @ctx.context
    def testcall():
        ctx.var1 = 2
        assert ctx.var1 == 2
        # removes newly assigned value
        del ctx.var1
        assert ctx.var1 == 1
        # removes outter-visible value:
        del ctx.var1

        with pytest.raises(AttributeError):
            ctx.var1

        # can't be erased again as well.
        with pytest.raises(AttributeError):
            del ctx.var1

    ctx.var1 = 1
    testcall()
    # Value deleted in inner context must be available here
    assert ctx.var1 == 1


def test_context_inner_function_deleting_attribute_can_reassign_it():
    context_keys = set()

    ctx = ContextLocal()

    @ctx.context
    def testcall():
        ctx.var1 = 2
        assert ctx.var1 == 2
        del ctx.var1
        assert ctx.var1 == 1
        del ctx.var1
        with pytest.raises(AttributeError):
            ctx.var1
        ctx.var1 = 3
        assert ctx.var1 == 3


    ctx.var1 = 1
    testcall()
    # Value deleted in inner context must be available here
    assert ctx.var1 == 1


def test_context_inner_function_reassigning_deleted_value_on_deletion_of_reassignemnt_should_not_see_outer_value():
    context_keys = set()

    ctx = ContextLocal()

    @ctx.context
    def testcall():
        ctx.var1 = 2
        assert ctx.var1 == 2
        del ctx.var1
        assert ctx.var1 == 1
        del ctx.var1
        with pytest.raises(AttributeError):
            ctx.var1
        ctx.var1 = 3
        assert ctx.var1 == 3
        del ctx.var1
        # Previously deleted value should remain "deleted"
        with pytest.raises(AttributeError):
            ctx.var1

    ctx.var1 = 1
    testcall()
    # Value deleted in inner context must be available here
    assert ctx.var1 == 1



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
    # WIP: to be used to test for memory leaks in
    # repeatedly called functions generators and co-routines
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

def test_contexts_keep_separate_variables():
    c1 = ContextLocal()
    c2 = ContextLocal()

    @c1.context
    @c2.context
    def inner():
        c1.a = 1
        c2.a = 2
        assert c1.a == 1
        assert c2.a == 2
        del c2.a
        with pytest.raises(AttributeError):
            c2.a
        assert c1.a == 1

    inner()

@pytest.mark.skip
def test_context_dir(self):
    pass
