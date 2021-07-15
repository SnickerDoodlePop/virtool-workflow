import inspect
from functools import wraps
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, NewType, Protocol, runtime_checkable

FixtureValue = NewType('FixtureValue', Any)
"""A return value from a :class:`Fixture` callable."""


@runtime_checkable
class Fixture(Protocol):
    """
    A Protocol formally defining any attributes which are 
    to a fixture function via @:func:`fixture`.

    Enables `isinstance(function, Fixture)` checks to be made.

    """
    __name__: str
    __is_fixture__: bool = True

    async def __call__(self, *args, **kwargs) -> FixtureValue:
        ...


_fixtures = ContextVar("fixtures")


def get_fixtures():
    """get the fixtures dictionary for the current context."""
    try:
        return _fixtures.get()
    except LookupError:
        _fixtures.set({})
        return _fixtures.get()


@contextmanager
def fixture_context(*fixtures: Fixture, copy_context=True) -> Dict[str, Fixture]:
    """
    Enter a new fixture context.

    Any fixtures added within the `with` block will no not be available outside of it.

    :param fixtures: Any fixtures which should be included in the context.
                     If a fixture with the same name is already present, the 
                     new fixture will be used instead.
    :param copy_context: Copy the fixtures dict from the current context, defaults to True.
                     

    :yield: A dictionary mapping fixture names to :class:`Fixture` functions.
    """
    if copy_context is True:
        current_fixtures = get_fixtures()
        _fixtures_copy = current_fixtures.copy()
    else:
        _fixtures_copy = {}

    for fixture in fixtures:
        _fixtures_copy[fixture.__name__] = fixture

    token = _fixtures.set(_fixtures_copy)

    try:
        yield _fixtures.get()
    finally:
        _fixtures.reset(token)


def runs_in_new_fixture_context(function: callable):
    """Decorator which causes the function to be executed in a new fixture context."""
    if inspect.iscoroutinefunction(function):
        @wraps(function)
        async def _in_new_context(*args, **kwargs):
            with fixture_context():
                return await function(*args, **kwargs)
    else:
        @wraps(function)
        def _in_new_context(*args, **kwargs):
            with fixture_context():
                return function(*args, **kwargs)

    return _in_new_context


