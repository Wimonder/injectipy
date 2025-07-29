import pytest

from injectipy.models.inject import Inject
from injectipy.store import InjectipyStore


def test_create_store() -> None:
    store = InjectipyStore()
    assert isinstance(store, InjectipyStore)


@pytest.fixture
def store() -> InjectipyStore:
    store_instance = InjectipyStore()
    store_instance._reset_for_testing()
    return store_instance


@pytest.mark.parametrize(
    "key,value",
    [(int, 1), ("foo", "bar"), (object, object())],
)
def test_register_value(store: InjectipyStore, key, value) -> None:
    store.register_value(key, value)
    assert store[key] == value


def test_key_not_found(store: InjectipyStore) -> None:
    with pytest.raises(KeyError):
        store[object]


def test_duplicate_key(store: InjectipyStore) -> None:
    store.register_value("foo", "bar")
    with pytest.raises(ValueError):
        store.register_value("foo", "bar")


@pytest.mark.parametrize(
    "key,resolver",
    [
        (int, lambda: 1),
        ("foo", lambda: "bar"),
    ],
)
def test_register_simple_resolver(store: InjectipyStore, key, resolver) -> None:
    store.register_resolver(key, resolver)
    result = store[key]
    assert result == resolver()


def test_register_resolver_with_injected_args_by_param_name(
    store: InjectipyStore,
) -> None:
    def resolver(foo: str, bar: str) -> str:
        return f"{foo} {bar}"

    store.register_value("foo", "hello")
    store.register_value("bar", "world")
    store.register_resolver("resolved", resolver)


def test_register_resolver_with_injected_args_by_inject(
    store: InjectipyStore,
) -> None:
    def resolver(a: str = Inject["foo"], b: str = Inject["bar"]) -> str:
        return f"{a} {b}"

    store.register_value("foo", "hello")
    store.register_value("bar", "world")
    store.register_resolver("resolved", resolver)


def test_register_nested_resolvers(
    store: InjectipyStore,
) -> None:
    def resolver_a() -> str:
        return "a"

    def resolver_b(a: str = Inject["resolver_a"]) -> str:
        return f"{a} b"

    def resolver_c(b: str = Inject["resolver_b"]) -> str:
        return f"{b} c"

    store.register_resolver("resolver_a", resolver_a)
    store.register_resolver("resolver_b", resolver_b)
    store.register_resolver("resolver_c", resolver_c)

    assert store["resolver_c"] == "a b c"


@pytest.mark.parametrize(
    "key,resolver",
    [
        ("foo", lambda *args, **kwargs: ...),
        ("foo", lambda *args: ...),
        ("foo", lambda **kwargs: ...),
    ],
)
def test_register_resolver_with_wrong_parameter_kinds(store: InjectipyStore, key, resolver) -> None:
    with pytest.raises(ValueError):
        store.register_resolver(key, resolver)


def test_register_resolver_with_unregistered_parameters(
    store: InjectipyStore,
) -> None:
    def resolver(foo: str, bar: str) -> str:
        return f"{foo} {bar}"

    # Registration should succeed (forward references allowed)
    store.register_resolver("resolved", resolver)
    
    # But resolution should fail due to missing dependencies
    with pytest.raises(TypeError, match="missing .* required positional arguments"):
        store["resolved"]


def test_register_evaluate_once_resolver(
    store: InjectipyStore,
) -> None:
    def resolver() -> object:
        return object()

    store.register_resolver("resolved", resolver, evaluate_once=True)

    assert store["resolved"] is store["resolved"]
