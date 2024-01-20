"""DependencyScope operations and functionality tests."""

import pytest

from injectipy import (
    DependencyNotFoundError,
    DependencyScope,
    DuplicateRegistrationError,
    Inject,
    InvalidStoreOperationError,
)


@pytest.fixture
def scope():
    """Provide a clean scope for each test."""
    return DependencyScope()


def test_create_scope():
    """Test scope creation."""
    scope = DependencyScope()
    assert scope is not None


@pytest.mark.parametrize(
    "key,value",
    [
        ("int", 1),
        ("foo", "bar"),
        (object, "value2"),
    ],
)
def test_register_value(scope: DependencyScope, key, value):
    """Test registering static values."""
    with scope:
        scope.register_value(key, value)
        assert scope[key] == value


def test_register_resolver(scope: DependencyScope):
    """Test registering resolver functions."""
    with scope:
        scope.register_resolver("dynamic", lambda: "resolved")
        assert scope["dynamic"] == "resolved"


def test_scope_contains(scope: DependencyScope):
    """Test contains method."""
    with scope:
        scope.register_value("key", "value")
        assert scope.contains("key")
        assert not scope.contains("nonexistent")


def test_scope_iteration(scope: DependencyScope):
    """Test scope contains method with multiple keys."""
    with scope:
        scope.register_value("key1", "value1")
        scope.register_value("key2", "value2")

        # Test that both keys are registered
        assert scope.contains("key1")
        assert scope.contains("key2")
        assert not scope.contains("key3")


def test_duplicate_registration_error(scope: DependencyScope):
    """Test duplicate key registration error."""
    scope.register_value("duplicate", "first")

    with pytest.raises(DuplicateRegistrationError):
        scope.register_value("duplicate", "second")


def test_direct_assignment_not_allowed(scope: DependencyScope):
    """Test that direct assignment raises error."""
    with pytest.raises(InvalidStoreOperationError):
        scope["key"] = "value"


def test_missing_key_error(scope: DependencyScope):
    """Test accessing missing key raises error."""
    with pytest.raises(DependencyNotFoundError):
        _ = scope["nonexistent"]


def test_resolver_with_dependencies(scope: DependencyScope):
    """Test resolver that depends on other registered values."""
    with scope:
        scope.register_value("base", "foundation")

        def dependent_resolver(base_dep: str = Inject["base"]) -> str:
            return f"built_on_{base_dep}"

        scope.register_resolver("dependent", dependent_resolver)
        assert scope["dependent"] == "built_on_foundation"


def test_evaluate_once_caching(scope: DependencyScope):
    """Test evaluate_once=True caches resolver results."""
    call_count = 0

    def counting_resolver() -> str:
        nonlocal call_count
        call_count += 1
        return f"call_{call_count}"

    scope.register_resolver("cached", counting_resolver, evaluate_once=True)

    # First call should execute resolver
    result1 = scope["cached"]
    assert result1 == "call_1"
    assert call_count == 1

    # Second call should return cached result
    result2 = scope["cached"]
    assert result2 == "call_1"  # Same result
    assert call_count == 1  # Not called again


def test_context_manager_cleanup():
    """Test context manager cleanup."""
    scope = DependencyScope()
    scope.register_value("key", "value")

    with scope:
        assert scope.is_active()
        assert scope["key"] == "value"

    assert not scope.is_active()
    # After exit, the scope should be cleaned up
    with pytest.raises(DependencyNotFoundError):
        _ = scope["key"]


def test_nested_scopes():
    """Test nested scope behavior."""
    outer = DependencyScope()
    inner = DependencyScope()

    outer.register_value("outer", "outer_value")
    inner.register_value("inner", "inner_value")

    with outer:
        with inner:
            # Inner scope should be active
            assert inner.is_active()
            assert inner["inner"] == "inner_value"

        # After inner scope exits, outer should still be active
        assert outer.is_active()
        assert outer["outer"] == "outer_value"


def test_method_chaining():
    """Test that registration methods support chaining."""
    scope = DependencyScope()
    result = scope.register_value("key1", "value1").register_resolver("key2", lambda: "value2")
    assert result is scope

    with scope:
        assert scope["key1"] == "value1"
        assert scope["key2"] == "value2"
