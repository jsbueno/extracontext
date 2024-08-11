

"""
# This snippet is an example in PEP 550
# which was relinquished in the final PEP 567 implementation

# i.e. it will fail in current Python contextvars

import contextvars

var1 = contextvars.ContextVar('var1')
var2 = contextvars.ContextVar('var2')

def gen():
    var1.set('gen')
    assert var1.get() == 'gen'
    assert var2.get() == 'main'
    yield 1

    # Modification to var1 in main() is shielded by
    # gen()'s local modification.
    assert var1.get() == 'gen'

    # But modifications to var2 are visible
    assert var2.get() == 'main modified'
    yield 2

def main():
    g = gen()

    var1.set('main')
    var2.set('main')
    next(g)

    # Modification of var1 in gen() is not visible.
    assert var1.get() == 'main'

    var1.set('main modified')
    var2.set('main modified')
    next(g)
"""
import pytest

from extracontext import PyContextLocal, NativeContextLocal

@pytest.mark.parametrize(["ContextClass"], [
    (PyContextLocal,),
    (NativeContextLocal,)
])
def test_pep550_generators_preserving(ContextClass):
    """Attributed shielding for test_pep550_generators_preserving

    As Proposed by PEP550, but not implemented by PEP 567
    """

    ctx = ContextClass()

    @ctx
    def gen():
        ctx.var1 = 'gen'

        ctx.var1 == 'gen'
        ctx.var2 == 'main'
        yield 1

        # Modification to var1 in main() is shielded by
        # gen()'s local modification.
        assert ctx.var1 == 'gen'

        # But modifications to var2 are visible
        ctx.var2 == 'main modified'
        yield 2

    # def main():
    ctx.var1 = 'main'
    ctx.var2 = 'main'

    g = gen()

    next(g)

    # Modification of var1 in gen() is not visible.
    assert ctx.var1 == 'main'

    ctx.var1 = 'main modified'
    ctx.var2 = 'main modified'
    next(g)


@pytest.mark.parametrize(["ContextClass"], [
    (PyContextLocal,),
    pytest.param(NativeContextLocal, marks=pytest.mark.skip)
])
def test_pep550_generators_preserving_after_gen_created(ContextClass):
    """Attributed shielding for test_pep550_generators_preserving

    As Proposed by PEP550, but not implemented by PEP 567
    """

    ctx = ContextClass()

    @ctx
    def gen():
        ctx.var1 = 'gen'

        ctx.var1 == 'gen'
        ctx.var2 == 'main'
        yield 1

        # Modification to var1 in main() is shielded by
        # gen()'s local modification.
        assert ctx.var1 == 'gen'

        # But modifications to var2 are visible
        ctx.var2 == 'main modified'
        yield 2

    # def main():

    g = gen()
    ctx.var1 = 'main'
    ctx.var2 = 'main'

    next(g)

    # Modification of var1 in gen() is not visible.
    assert ctx.var1 == 'main'

    ctx.var1 = 'main modified'
    ctx.var2 = 'main modified'
    next(g)

