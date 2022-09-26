import gc

import pytest

from extracontext import ContextMap


def test_context_local_vars_work_as_mapping():
    ctx = ContextMap()
    ctx["value"] = 1
    assert ctx["value"] == 1
    del ctx["value"]
    with pytest.raises(KeyError):
        assert ctx["value"] == 1


def test_contextmap_function_holds_unique_value_for_attribute():

    ctx = ContextMap()

    @ctx
    def testcall():
        assert ctx["var1"] == 1
        ctx["var1"] = 2
        assert ctx["var1"] == 2
        del ctx["var1"]

    ctx["var1"] = 1
    assert ctx["var1"] == 1
    testcall()
    assert ctx["var1"] == 1


def test_context_inner_function_cant_erase_outter_value():

    ctx = ContextMap()

    @ctx
    def testcall():
        ctx["var1"] = 2
        assert ctx["var1"] == 2
        del ctx["var1"]

    ctx["var1"] = 1
    testcall()
    assert ctx["var1"] == 1


def test_context_inner_function_trying_to_erase_outter_value_blocks_cant_read_attribute_back():

    ctx = ContextMap()

    @ctx
    def testcall():
        ctx["var1"] = 2
        assert ctx["var1"] == 2
        # removes newly assigned value
        del ctx["var1"]

        with pytest.raises(KeyError):
            ctx["var1"]
        assert ctx.get("var1", None) is None

        # can't be erased again as well.
        with pytest.raises(KeyError):
            del ctx["var1"]

    ctx["var1"] = 1
    testcall()
    # Value deleted in inner context must be available here
    assert ctx["var1"] == 1


def test_contextmap_inner_function_deleting_attribute_can_reassign_it():

    ctx = ContextMap()

    @ctx
    def testcall():
        ctx["var1"] = 2
        assert ctx["var1"] == 2
        del ctx["var1"]
        with pytest.raises(KeyError):
            ctx["var1"]
        ctx["var1"] = 3
        assert ctx["var1"] == 3

    ctx["var1"] = 1
    testcall()
    # Value deleted in inner context must be available here
    assert ctx["var1"] == 1


def test_contextmap_inner_function_reassigning_deleted_value_on_deletion_of_reassignemnt_should_not_see_outer_value():

    ctx = ContextMap()

    @ctx
    def testcall():
        ctx["var1"] = 2
        assert ctx["var1"] == 2
        del ctx["var1"]
        with pytest.raises(KeyError):
            ctx["var1"]
        ctx["var1"] = 3
        assert ctx["var1"] == 3
        del ctx["var1"]
        # Previously deleted value should remain "deleted"
        with pytest.raises(KeyError):
            ctx["var1"]

    ctx["var1"] = 1
    testcall()
    # Value deleted in inner context must be available here
    assert ctx["var1"] == 1


def test_contextmap_granddaugher_works_nice_with_daughter_deleting_attribute():

    ctx = ContextMap()

    @ctx
    def granddaughter():
        with pytest.raises(KeyError):
            ctx["var1"]
        ctx["var1"] = 2
        assert ctx["var1"] == 2

    @ctx
    def daughter():
        assert ctx["var1"] == 1
        del ctx["var1"]
        granddaughter()
        with pytest.raises(KeyError):
            ctx["var1"]

    ctx["var1"] = 1
    daughter()
    assert ctx["var1"] == 1


def test_contextmap_each_call_creates_unique_context_and_clean_up():
    # whitebox test - inner attributes checked:
    context_keys = set()

    ctx = ContextMap()

    @ctx
    def testcall():
        context_keys.update(ctx._registry.keys())

    for i in range(10):
        testcall()

    assert len(context_keys) == 10
    assert len(list(ctx._registry.keys())) == 0


def test_contextmap_unique_context_for_generators_is_cleaned_up():
    context_keys = set()

    ctx = ContextMap()

    @ctx
    def testcall():
        context_keys.update(k.value for k in ctx._registry.keys())
        yield None

    for i in range(100):
        for _ in testcall():
            pass
    gc.collect()

    assert len(context_keys) == 100
    assert len(list(ctx._registry.keys())) == 0


def test_contextmaps_keep_separate_variables():
    c1 = ContextMap()
    c2 = ContextMap()

    @c1
    @c2
    def inner():
        c1["a"] = 1
        c2["a"] = 2
        assert c1["a"] == 1
        assert c2["a"] == 2
        del c2["a"]
        with pytest.raises(KeyError):
            c2["a"]
        assert c1["a"] == 1

    inner()


def test_contextmap_keys():

    ctx = ContextMap()

    @ctx
    def testcall():

        ctx["var2"] = 2
        assert "var1" in ctx.keys()
        assert "var2" in ctx.keys()

        # removes visibility of key/value in outer context:
        del ctx["var1"]
        assert "var1" not in ctx.keys()

    ctx["var1"] = 1
    assert "var1" in ctx.keys()
    testcall()
    assert "var1" in ctx.keys()
    assert "var2" not in ctx.keys()


def test_contextmap_run_method_isolates_context():
    ctx = ContextMap()

    def testcall():
        assert ctx["var1"] == 1
        ctx["var1"] = 2
        assert ctx["var1"] == 2

    ctx["var1"] = 1
    assert ctx["var1"] == 1
    ctx._run(testcall)
    assert ctx["var1"] == 1


def test_contextmap_mapping_enter_new_context_in_with_block():

    ctx = ContextMap()

    ctx["value"] = 1

    with ctx:
        ctx["value"] = 2
        assert ctx["value"] == 2

    assert ctx["value"] == 1
