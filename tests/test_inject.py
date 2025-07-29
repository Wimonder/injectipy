import pytest

from injectipy import inject
from injectipy.models.inject import Inject
from injectipy.store import InjectipyStore


@pytest.fixture
def store() -> InjectipyStore:
    store_instance = InjectipyStore()
    store_instance._reset_for_testing()
    return store_instance


def test_inject_function(store: InjectipyStore) -> None:
    store.register_value("bar", "baz")

    @inject
    def foo(bar: str = Inject["bar"]) -> str:
        return bar

    assert foo() == "baz"


def test_inject_overwrite_defaults(store: InjectipyStore) -> None:
    store.register_value("bar", "baz")

    @inject
    def foo(bar: str = Inject["bar"]) -> str:
        return bar

    assert foo("foo") == "foo"


def test_inject_constructor(store: InjectipyStore) -> None:
    store.register_value("bar", "baz")

    class Foo:
        @inject
        def __init__(self, bar: str = Inject["bar"]) -> None:
            self.bar = bar

    assert Foo().bar == "baz"


def test_inject_non_existing_key(store: InjectipyStore) -> None:
    @inject
    def foo(bar: str = Inject["bar"]) -> str:
        return bar

    with pytest.raises(RuntimeError):
        foo()
