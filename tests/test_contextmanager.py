import threading
import time
from collections import deque

from extracontext import ContextLocal

import pytest

consume = deque(maxlen=0).extend

def test_context_local_enter_new_context_in_with_block():

    ctx = ContextLocal()

    ctx.value = 1

    with ctx:
        ctx.value = 2
        assert ctx.value == 2

    assert ctx.value == 1


def test_context_local_in_with_block_can_see_outside_values():

    ctx = ContextLocal()

    ctx.value = 1

    with ctx:
        assert ctx.value == 1
        ctx.value = 2
        assert ctx.value == 2

    assert ctx.value == 1


def test_context_local_in_with_block_can_see_outside_values2():

    ctx = ContextLocal()

    ctx.value = 1
    ctx.value2 = 2

    with ctx:
        assert ctx.value == 1
        assert ctx.value2 == 2
        ctx.value = 3
        assert ctx.value == 3
        assert ctx.value2 == 2

    assert ctx.value2 == 2
    assert ctx.value == 1


def test_context_local_enter_new_context_in_nested_with_blocks():

    ctx = ContextLocal()

    ctx.value = 1

    with ctx:
        ctx.value = 2
        with ctx:
            ctx.value = 3
            with ctx:
                ctx.value = 4
                assert ctx.value == 4
            assert ctx.value == 3
        assert ctx.value == 2

    assert ctx.value == 1


def test_context_local_in_with_block_dont_mixup_with_other_context():

    ctx1 = ContextLocal()
    ctx2 = ContextLocal()

    ctx1.value = 1
    ctx2.value = 2

    with ctx1:
        ctx1.value = 3
        with ctx2:
            assert ctx1.value == 3
            ctx2.value = 4
            assert ctx1.value == 3
            assert ctx2.value == 4
            with ctx1:
                ctx1.value = 5
                assert ctx1.value == 5
                assert ctx2.value == 4
            assert ctx2.value == 4
            assert ctx1.value == 3

        assert ctx1.value == 3
        assert ctx2.value == 2

    assert ctx1.value == 1
    assert ctx2.value == 2


def test_context_in_with_block_deleted_var_must_be_undeleted_outside():

    ctx = ContextLocal()

    ctx.value = 1

    with ctx:
        ctx.value = 2
        assert ctx.value == 2
        del ctx.value
        assert ctx.value == 1
        del ctx.value
        with pytest.raises(AttributeError):
            assert ctx.value

    assert ctx.value == 1


def test_context_in_with_block_deleted_var_must_be_undeleted_outside_even_after_set_again():

    ctx = ContextLocal()

    ctx.value = 1

    with ctx:
        ctx.value = 2
        assert ctx.value == 2
        del ctx.value
        assert ctx.value == 1
        del ctx.value
        with pytest.raises(AttributeError):
            assert ctx.value
        ctx.value = 3
        assert ctx.value == 3
        del ctx.value
        with pytest.raises(AttributeError):
            assert ctx.value


    assert ctx.value == 1

