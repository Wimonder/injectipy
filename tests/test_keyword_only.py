"""Tests for keyword-only parameter injection support."""

import pytest

from injectipy import Inject, InjectipyStore, inject


@pytest.fixture
def store() -> InjectipyStore:
    store_instance = InjectipyStore()
    store_instance._reset_for_testing()
    return store_instance


def test_keyword_only_inject_basic(store: InjectipyStore):
    """Test basic keyword-only parameter injection."""
    store.register_value("service", "injected_service")

    @inject
    def func(a, *, b=Inject["service"], c="default"):
        return f"a={a}, b={b}, c={c}"

    result = func("test")
    assert result == "a=test, b=injected_service, c=default"


def test_keyword_only_inject_override(store: InjectipyStore):
    """Test overriding keyword-only injected parameter."""
    store.register_value("service", "injected_service")

    @inject
    def func(a, *, b=Inject["service"], c="default"):
        return f"a={a}, b={b}, c={c}"

    # Override injected parameter
    result = func("test", b="override")
    assert result == "a=test, b=override, c=default"

    # Override regular parameter
    result = func("test", c="custom")
    assert result == "a=test, b=injected_service, c=custom"

    # Override both
    result = func("test", b="override", c="custom")
    assert result == "a=test, b=override, c=custom"


def test_keyword_only_multiple_inject(store: InjectipyStore):
    """Test multiple keyword-only Inject parameters."""
    store.register_value("service1", "injected_service1")
    store.register_value("service2", "injected_service2")

    @inject
    def func(a, *, b=Inject["service1"], c=Inject["service2"], d="default"):
        return f"a={a}, b={b}, c={c}, d={d}"

    result = func("test")
    assert result == "a=test, b=injected_service1, c=injected_service2, d=default"

    # Override one injection
    result = func("test", b="override1")
    assert result == "a=test, b=override1, c=injected_service2, d=default"

    # Override both injections
    result = func("test", b="override1", c="override2")
    assert result == "a=test, b=override1, c=override2, d=default"


def test_keyword_only_mixed_with_regular(store: InjectipyStore):
    """Test mixing regular and keyword-only Inject parameters."""
    store.register_value("service1", "injected_service1")
    store.register_value("service2", "injected_service2")

    @inject
    def func(a, b=Inject["service1"], *, c=Inject["service2"], d="default"):
        return f"a={a}, b={b}, c={c}, d={d}"

    result = func("test")
    assert result == "a=test, b=injected_service1, c=injected_service2, d=default"

    # Override regular injection positionally
    result = func("test", "override1")
    assert result == "a=test, b=override1, c=injected_service2, d=default"

    # Override keyword-only injection
    result = func("test", c="override2")
    assert result == "a=test, b=injected_service1, c=override2, d=default"

    # Override both
    result = func("test", "override1", c="override2")
    assert result == "a=test, b=override1, c=override2, d=default"


def test_keyword_only_missing_dependency(store: InjectipyStore):
    """Test keyword-only parameter with missing dependency."""

    @inject
    def func(a, *, b=Inject["missing_service"]):
        return f"a={a}, b={b}"

    with pytest.raises(RuntimeError, match="Could not resolve missing_service"):
        func("test")


def test_keyword_only_only_inject(store: InjectipyStore):
    """Test function with only keyword-only Inject parameters."""
    store.register_value("service", "injected_service")

    @inject
    def func(*, a=Inject["service"], b="default"):
        return f"a={a}, b={b}"

    result = func()
    assert result == "a=injected_service, b=default"

    result = func(a="override")
    assert result == "a=override, b=default"

    result = func(b="custom")
    assert result == "a=injected_service, b=custom"


def test_keyword_only_no_inject_defaults():
    """Test that functions with only regular keyword-only defaults are not wrapped."""

    @inject
    def func(a, *, b="default", c="another"):
        return f"a={a}, b={b}, c={c}"

    # Function should not be wrapped since no Inject defaults
    result = func("test")
    assert result == "a=test, b=default, c=another"

    result = func("test", b="custom")
    assert result == "a=test, b=custom, c=another"


def test_keyword_only_exception_handling(store: InjectipyStore):
    """Test that defaults are restored even if function raises exception."""
    store.register_value("service", "injected_service")

    @inject
    def failing_func(a, *, b=Inject["service"]):
        if a == "fail":
            raise ValueError("Intentional failure")
        return f"a={a}, b={b}"

    # First call should work
    result = failing_func("success")
    assert result == "a=success, b=injected_service"

    # Function that raises exception
    with pytest.raises(ValueError, match="Intentional failure"):
        failing_func("fail")

    # Subsequent call should still work (defaults properly restored)
    result = failing_func("success")
    assert result == "a=success, b=injected_service"


def test_keyword_only_preserve_signature():
    """Test that function signature is preserved with keyword-only parameters."""
    store = InjectipyStore()
    store._reset_for_testing()
    store.register_value("service", "injected_service")

    @inject
    def func(a: str, *, b: str = Inject["service"], c: str = "default") -> str:
        return f"a={a}, b={b}, c={c}"

    # Check that signature information is preserved
    import inspect

    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    assert len(params) == 3
    assert params[0].name == "a"
    assert params[0].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params[1].name == "b"
    assert params[1].kind == inspect.Parameter.KEYWORD_ONLY
    assert params[2].name == "c"
    assert params[2].kind == inspect.Parameter.KEYWORD_ONLY

    # Check that annotations are preserved
    assert sig.return_annotation == str
    assert params[0].annotation == str
    assert params[1].annotation == str
    assert params[2].annotation == str
