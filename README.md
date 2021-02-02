Context Local Variables
==========================


Context Local Variables meant to enable
separate variable values for code running either
in asyncio, using generators, or multiple-threads.


These are meant to be simpler to use and work in more scenarios than
Python's contextvars.

Usage:

Create one or more project-wide instances of "extracontext.ContextLocal"
Decorate your functions, co-routines, worker-methods and generators
that should hold their own states with that instance's `context` method -

and use the instance as namespace for private variables that will be local
and non-local until entering another callable decorated
with `intance.context` - that will create a new, separated scope
visible inside  the decorated callable.


Example:

