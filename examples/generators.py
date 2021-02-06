"""
Initial problem example that led to the creation of this project.

This example was originally written by @jdehesa,
trying to achieve the results here by using Python's contextvars

https://stackoverflow.com/questions/53611690/how-do-i-write-consistent-stateful-context-managers/57448146


"""

# Code demonstrating how generators
# entered in different calls can each
# have a separate context


from contextlib import contextmanager
#from contextvars import ContextVar, Context, copy_context

from extracontext import ContextLocal

ctx = ContextLocal()


@contextmanager
def use_mode(mode):
    ctx.MODE = mode
    print("entering use_mode")
    print_mode()
    try:
        yield
    finally:

        pass

def print_mode():
   print(f'Mode {ctx.MODE}')


@ctx
def first():
    ctx.MODE = 0
    print('Start first')
    print_mode()
    with use_mode(1):
        print('In first: with use_mode(1)')
        print('In first: start second')
        it = second()
        next(it)
        print('In first: back from second')
        print_mode()
        print('In first: continue second')
        next(it, None)
        print('In first: finish')
        print_mode()
    print("at end")
    print_mode()

@ctx
def second():
    print('Start second')
    print_mode()
    with use_mode(2):
        print('In second: with use_mode(2)')
        print('In second: yield')
        yield
        print('In second: continue')
        print_mode()
        print('In second: finish')

first()
