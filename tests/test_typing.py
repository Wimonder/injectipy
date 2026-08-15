"""Typing contract tests.

These are checked by mypy in CI and run by pytest as a smoke test. A regression in
the decorator or Inject overloads shows up as a mypy failure here.
"""

import asyncio

from injectipy import DependencyScope, Inject, ainject, inject


class Service:
    def work(self) -> str:
        return "work"


explicit_scope = DependencyScope()


@inject
def with_type_key(service: Service = Inject[Service]) -> str:
    return service.work()


@inject
def with_string_key(name: str = Inject["name"]) -> str:
    return name


@inject(scopes=[explicit_scope])
def with_explicit_scope(service: Service = Inject[Service]) -> str:
    return service.work()


@ainject
async def async_with_type_key(service: Service = Inject[Service]) -> str:
    return service.work()


# A mismatched annotation must stay an error. warn_unused_ignores turns a regression
# in the Inject overloads into a mypy failure here.
@inject
def mismatched_annotation(service: int = Inject[Service]) -> int:  # type: ignore[assignment]
    return service


def test_decorated_functions_keep_their_signature() -> None:
    """Test that decorated functions stay callable with their own return type."""
    scope = DependencyScope()
    scope.register_value(Service, Service())
    scope.register_value("name", "injectipy")

    with scope:
        from_type_key: str = with_type_key()
        from_string_key: str = with_string_key()
        assert from_type_key == "work"
        assert from_string_key == "injectipy"


def test_explicit_scope_decorator() -> None:
    """Test the decorator form that takes scopes."""
    explicit_scope.register_value(Service, Service(), replace=True)
    assert with_explicit_scope() == "work"


def test_async_decorated_function() -> None:
    """Test that ainject keeps the coroutine return type."""
    scope = DependencyScope()
    scope.register_value(Service, Service())

    async def run() -> str:
        async with scope:
            return await async_with_type_key()

    assert asyncio.run(run()) == "work"
