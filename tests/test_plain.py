import gc
import sys
from collections.abc import Mapping, Sequence

import pytest

from extracontext import ContextLocal, PyContextLocal, NativeContextLocal


@pytest.mark.parametrize(
    ["ContextClass", "backend"],
    [(PyContextLocal, "python"), (NativeContextLocal, "native")],
)
def test_backend_can_be_picked_by_keyword(ContextClass, backend):
    ctx = ContextLocal(backend=backend)
    assert isinstance(ctx, ContextClass)


def test_default_backend_is_native():
    ctx = ContextLocal()
    assert isinstance(ctx, NativeContextLocal)


def test_direct_instantion_of_subclasses_works():
    # The "route to subclass based on backend" pattern failed at least once during development.
    assert isinstance(PyContextLocal(), PyContextLocal)
    assert isinstance(NativeContextLocal(), NativeContextLocal)


@pytest.mark.parametrize(["ContextClass"], [(PyContextLocal,), (NativeContextLocal,)])
def test_context_local_vars_work_as_namespace(ContextClass):
    ctx = ContextClass()
    ctx.value = 1
    assert ctx.value == 1
    del ctx.value
    with pytest.raises(AttributeError):
        assert ctx.value == 1


@pytest.mark.parametrize(["ContextClass"], [(PyContextLocal,), (NativeContextLocal,)])
def test_context_function_holds_unique_value_for_attribute(ContextClass):
    ctx = ContextClass()
    called = False

    @ctx
    def testcall():
        nonlocal called
        called = True
        assert ctx.var1 == 1
        ctx.var1 = 2
        assert ctx.var1 == 2
        del ctx.var1

    ctx.var1 = 1
    assert ctx.var1 == 1
    testcall()
    assert called
    assert ctx.var1 == 1


@pytest.mark.parametrize(["ContextClass"], [(PyContextLocal,), (NativeContextLocal,)])
def test_context_once_value_in_function_is_erased_outer_value_doesnot_gets_visible_back(
    ContextClass,
):

    ctx = ContextClass()
    called = False

    @ctx
    def testcall():
        nonlocal called
        called = True
        assert ctx.var1 == 1
        ctx.var1 = 2
        assert ctx.var1 == 2
        del ctx.var1
        with pytest.raises(AttributeError):
            assert ctx.var1 == 1

    ctx.var1 = 1
    assert ctx.var1 == 1
    testcall()
    assert called
    assert ctx.var1 == 1


@pytest.mark.parametrize(["ContextClass"], [(PyContextLocal,), (NativeContextLocal,)])
def test_context_inner_function_cant_erase_outter_value(ContextClass):

    ctx = ContextClass()
    called = False

    @ctx
    def testcall():
        nonlocal called
        called = True
        ctx.var1 = 2
        assert ctx.var1 == 2
        del ctx.var1

    ctx.var1 = 1
    testcall()
    assert called
    assert ctx.var1 == 1


@pytest.mark.parametrize(["ContextClass"], [(PyContextLocal,), (NativeContextLocal,)])
def test_context_inner_function_trying_to_erase_outter_value_blocks_cant_read_attribute_back(
    ContextClass,
):

    ctx = ContextClass()

    called = False

    @ctx
    def testcall():
        nonlocal called
        called = True
        ctx.var1 = 2
        assert ctx.var1 == 2
        # removes newly assigned value
        del ctx.var1
        with pytest.raises(AttributeError):
            ctx.var1
        assert getattr(ctx, "var1", None) is None

        # can't be erased again as well.
        with pytest.raises(AttributeError):
            del ctx.var1

    ctx.var1 = 1
    testcall()
    assert called
    # Value deleted in inner context must be available here
    assert ctx.var1 == 1


@pytest.mark.parametrize(["ContextClass"], [(PyContextLocal,), (NativeContextLocal,)])
def test_context_inner_function_deleting_attribute_can_reassign_it(ContextClass):

    ctx = ContextClass()

    @ctx
    def testcall():
        ctx.var1 = 2
        assert ctx.var1 == 2
        del ctx.var1
        with pytest.raises(AttributeError):
            ctx.var1
        ctx.var1 = 3
        assert ctx.var1 == 3

    ctx.var1 = 1
    testcall()
    # Value deleted in inner context must be available here
    assert ctx.var1 == 1


@pytest.mark.parametrize(["ContextClass"], [(PyContextLocal,), (NativeContextLocal,)])
def test_context_inner_function_reassigning_deleted_value_on_deletion_of_reassignemnt_should_not_see_outer_value(
    ContextClass,
):

    ctx = ContextClass()

    @ctx
    def testcall():
        ctx.var1 = 2
        assert ctx.var1 == 2
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


@pytest.mark.parametrize(["ContextClass"], [(PyContextLocal,), (NativeContextLocal,)])
def test_context_granddaugher_works_nice_with_daughter_deleting_attribute(ContextClass):

    ctx = ContextClass()

    @ctx
    def granddaughter():
        with pytest.raises(AttributeError):
            ctx.var1
        ctx.var1 = 2
        assert ctx.var1 == 2

    @ctx
    def daughter():
        assert ctx.var1 == 1
        del ctx.var1
        granddaughter()
        with pytest.raises(AttributeError):
            ctx.var1

    ctx.var1 = 1
    daughter()
    assert ctx.var1 == 1


# Python implementation only:
def test_each_call_creates_unique_context_and_clean_up():
    context_keys = set()

    ctx = PyContextLocal()

    @ctx
    def testcall():
        context_keys.update(ctx._et_registry.keys())

    for i in range(10):
        testcall()

    assert len(context_keys) == 10
    assert len(list(ctx._et_registry.keys())) == 0


def test_unique_context_for_generators_is_cleaned_up():
    context_keys = set()

    ctx = PyContextLocal()

    @ctx
    def testcall():
        context_keys.update(k.value for k in ctx._et_registry.keys())
        yield None

    for i in range(100):
        for _ in testcall():
            pass
    gc.collect()

    assert len(context_keys) == 100
    assert len(list(ctx._et_registry.keys())) == 0


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


# def test_abusive_memory_leak():
# ctx = PyContextLocal()

# @ctx
# def func(n):


def test_contexts_keep_separate_variables():
    c1 = PyContextLocal()
    c2 = PyContextLocal()

    @c1
    @c2
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


def test_context_dir():

    ctx = PyContextLocal()

    @ctx
    def testcall():

        ctx.var2 = 2
        assert "var1" in dir(ctx)
        assert "var2" in dir(ctx)

        del ctx.var1

    ctx.var1 = 1
    assert "var1" in dir(ctx)
    testcall()
    assert "var1" in dir(ctx)
    assert "var2" not in dir(ctx)


@pytest.mark.parametrize(["ContextClass"], [(PyContextLocal,), (NativeContextLocal,)])
def test_dir_context_should_not_show_deleted_attributes(ContextClass):
    ctx = ContextClass()

    called = False

    @ctx
    def testcall():
        nonlocal called
        called = True
        assert set(dir(ctx)) == {
            "var1",
        }
        ctx.var1 = 2
        assert set(dir(ctx)) == {
            "var1",
        }
        # removes newly assigned value
        del ctx.var1
        assert dir(ctx) == []

    ctx.var1 = 1
    testcall()
    assert called
    # Value deleted in inner context must be available here
    assert set(dir(ctx)) == {
        "var1",
    }
    assert ctx.var1 == 1


@pytest.mark.parametrize(["ContextClass"], [(PyContextLocal,), (NativeContextLocal,)])
def test_dir_context_should_work_with_intermediate_deleted_attribute(ContextClass):
    ctx = ContextClass()

    called = False

    @ctx
    def testcall_level2():
        nonlocal called
        called = True
        assert dir(ctx) == []
        ctx.var1 = 2
        assert set(dir(ctx)) == {
            "var1",
        }

    @ctx
    def testcall():
        del ctx.var1
        assert dir(ctx) == []
        testcall_level2()
        assert dir(ctx) == []

    ctx.var1 = 1
    testcall()
    assert called
    # Value deleted in inner context must be available here
    assert ctx.var1 == 1
    assert set(dir(ctx)) == {
        "var1",
    }


def test_context_run_method_isolates_context():

    ctx = PyContextLocal()

    def testcall():
        assert ctx.var1 == 1
        ctx.var1 = 2
        assert ctx.var1 == 2
        del ctx.var1

    ctx.var1 = 1
    assert ctx.var1 == 1
    ctx._run(testcall)
    assert ctx.var1 == 1
