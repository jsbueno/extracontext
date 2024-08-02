"""
Initial problem example that led to the creation of this project.

This example was originally written by @jdehesa,
trying to achieve the results here by using Python's contextvars

https://stackoverflow.com/questions/53611690/how-do-i-write-consistent-stateful-context-managers/57448146


"""

from contextlib import contextmanager

import pytest

from extracontext import ContextLocal, ContextError, NativeContextLocal


@pytest.mark.parametrize(["ContextClass"], [
    (ContextLocal,),
    (NativeContextLocal,)
])
def test_context_local_vars_work_as_decorator(ContextClass):
    ctx = ContextClass()

    @ctx
    def func():
        ctx.value = 1
        assert ctx.value == 1

    func()
    with pytest.raises(AttributeError):
        assert ctx.value == 1


@pytest.mark.parametrize(["ContextClass"], [
    (ContextLocal,),
    (NativeContextLocal,)
])
def test_context_local_doesnt_leak_from_generator(ContextClass):
    ctx = ContextClass()

    @ctx
    def gen():
        ctx.value = 2
        yield
        assert ctx.value == 2

    ctx.value = 1
    g = gen()
    assert ctx.value == 1
    next(g)
    assert ctx.value == 1
    next(g, None)
    assert ctx.value == 1


@pytest.mark.parametrize(["ContextClass"], [
    (ContextLocal,),
    (NativeContextLocal,)
])
def test_context_local_works_with_generator_send(ContextClass):
    ctx = ContextClass()

    sentinel = object()

    @ctx
    def gen():
        ctx.value = 2
        value = yield
        assert value is not None
        assert ctx.value == 2
        yield value
        return value

    ctx.value = 1
    g = gen()
    assert ctx.value == 1
    next(g)
    assert ctx.value == 1
    value = g.send(sentinel)
    assert value is sentinel
    try:
        next(g)
    except StopIteration as stop:
        assert stop.value is sentinel
    else:
        assert False, "StopIteration not raised"
    assert ctx.value == 1

@pytest.mark.parametrize(["ContextClass"], [
    (ContextLocal,),
    (NativeContextLocal,)
])
def test_context_local_works_with_generator_throw(ContextClass):
    ctx = ContextClass()

    sentinel = object()

    @ctx
    def gen():
        ctx.value = 2
        with pytest.raises(RuntimeError):
            value = yield
        assert ctx.value == 2

    ctx.value = 1
    g = gen()
    assert ctx.value == 1
    next(g)
    assert ctx.value == 1
    try:
        g.throw(RuntimeError())
    except StopIteration as stop:
        pass
    else:
        assert False, "StopIteration not raised"
    assert ctx.value == 1


@pytest.mark.parametrize(["ContextClass"], [
    (ContextLocal,),
    (NativeContextLocal,)
])
def test_context_local_vars_work_for_generators(ContextClass):

    ctx = ContextClass()

    results  = []

    @contextmanager
    def use_mode(mode):
        previous = ctx.mode
        ctx.mode = mode
        try:
            yield
        finally:
            ctx.mode = previous

    @ctx
    def first():
        ctx.mode = 0
        results.append(("starting", ctx.mode))
        with use_mode(1):
            results.append(("entered first", ctx.mode))
            it = second()
            next(it)
            results.append(("back in first", ctx.mode))
            next(it, None)
            results.append(("ended second", ctx.mode))
        results.append(("exited first context manager", ctx.mode))

    @ctx
    def second():
        with use_mode(2):
            results.append(("entered second", ctx.mode))
            yield
            results.append(("back in second", ctx.mode))
        results.append(("exited second context manager", ctx.mode))
    first()
    assert results ==  [
        ('starting', 0), ('entered first', 1), ('entered second', 2),
        ('back in first', 1), ('back in second', 2), ('exited second context manager', 1),
        ('ended second', 1), ('exited first context manager', 0)
    ]


