"""Tests for edge cases and error conditions in injectipy.

This module contains tests for various edge cases, error conditions,
and boundary scenarios to ensure robust behavior of the DI system.
"""

import pytest

from injectipy import Inject, InjectipyStore, inject

pytestmark = pytest.mark.edge_case


@pytest.fixture
def store() -> InjectipyStore:
    store_instance = InjectipyStore()
    store_instance._reset_for_testing()
    return store_instance


def test_setitem_not_implemented(store: InjectipyStore):
    """Test that __setitem__ raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="Use register_resolver or register_value instead"):
        store["key"] = "value"


def test_overwrite_cache_with_evaluate_once(store: InjectipyStore):
    """Test that evaluate_once resolvers cache results properly."""
    call_count = 0

    def resolver():
        nonlocal call_count
        call_count += 1
        return f"result_{call_count}"

    store.register_resolver("cached", resolver, evaluate_once=True)

    # First call should execute resolver
    result1 = store["cached"]
    assert result1 == "result_1"
    assert call_count == 1

    # Second call should return cached result
    result2 = store["cached"]
    assert result2 == "result_1"  # Same result
    assert call_count == 1  # No additional calls

    # Results should be identical objects
    assert result1 is result2


def test_resolver_with_partial_inject_dependencies(store: InjectipyStore):
    """Test resolver with mix of Inject and parameter name dependencies."""
    # Register some dependencies
    store.register_value("explicit_dep", "explicit_value")
    store.register_value("param_dep", "param_value")

    def resolver(
        explicit: str = Inject["explicit_dep"],
        param_dep: str = "param_default",  # This should be resolved by parameter name with default
        missing_param: str = "default_value",  # This has a default
    ):
        return f"{explicit}-{param_dep}-{missing_param}"

    store.register_resolver("mixed", resolver)
    result = store["mixed"]
    assert result == "explicit_value-param_value-default_value"


def test_resolver_with_missing_inject_dependency(store: InjectipyStore):
    """Test resolver behavior when Inject dependency is missing."""

    def resolver(missing_dep: str = Inject["missing_key"]):
        return f"resolved: {missing_dep}"

    store.register_resolver("failing", resolver)

    # The resolver will get the Inject object itself since the key doesn't exist
    # and there's no parameter name fallback
    result = store["failing"]
    assert "resolved: <injectipy.models.inject.Inject object" in result


def test_circular_dependency_path_detection(store: InjectipyStore):
    """Test that _has_dependency_path correctly detects paths."""

    # Create a dependency chain: A -> B -> C
    def resolver_a(b=Inject["b"]):
        return f"A({b})"

    def resolver_b(c=Inject["c"]):
        return f"B({c})"

    def resolver_c():
        return "C"

    store.register_resolver("a", resolver_a)
    store.register_resolver("b", resolver_b)
    store.register_resolver("c", resolver_c)

    # Test dependency path detection (requires visited set parameter)
    assert store._has_dependency_path("a", "c", set()) is True
    assert store._has_dependency_path("b", "c", set()) is True
    assert store._has_dependency_path("c", "a", set()) is False
    assert store._has_dependency_path("c", "b", set()) is False


def test_dependency_path_with_nonexistent_keys(store: InjectipyStore):
    """Test dependency path detection with non-existent keys."""
    # Test with completely non-existent keys
    assert store._has_dependency_path("nonexistent1", "nonexistent2", set()) is False

    # Test with one existing, one non-existent
    store.register_value("existing", "value")
    assert store._has_dependency_path("existing", "nonexistent", set()) is False
    assert store._has_dependency_path("nonexistent", "existing", set()) is False


def test_inject_decorator_no_defaults():
    """Test @inject decorator on function with no defaults returns original function."""

    @inject
    def func_no_defaults(a, b):
        return a + b

    # Should return the original function unchanged
    result = func_no_defaults(1, 2)
    assert result == 3


def test_inject_decorator_no_inject_defaults():
    """Test @inject decorator on function with non-Inject defaults."""

    @inject
    def func_regular_defaults(a, b="default"):
        return f"{a}-{b}"

    # Should return the original function unchanged
    result = func_regular_defaults("test")
    assert result == "test-default"


def test_inject_decorator_runtime_error_chaining():
    """Test that RuntimeError properly chains the original KeyError."""

    @inject
    def failing_function(dep: str = Inject["missing_key"]):
        return f"Got: {dep}"

    with pytest.raises(RuntimeError) as exc_info:
        failing_function()

    # Verify the error message contains function info
    assert "Could not resolve missing_key for failing_function" in str(exc_info.value)
    assert "test_edge_cases" in str(exc_info.value)  # Module name

    # Verify the original KeyError is chained
    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, KeyError)


def test_inject_decorator_restores_defaults():
    """Test that @inject decorator properly restores defaults after each call."""
    store = InjectipyStore()
    store.register_value("dep", "injected_value")

    @inject
    def func_with_defaults(a, dep: str = Inject["dep"], c="default_c"):
        return f"{a}-{dep}-{c}"

    # Call multiple times to ensure defaults are properly managed
    result1 = func_with_defaults("test1")
    assert result1 == "test1-injected_value-default_c"

    result2 = func_with_defaults("test2")
    assert result2 == "test2-injected_value-default_c"

    # Override the injected parameter
    result3 = func_with_defaults("test3", "override")
    assert result3 == "test3-override-default_c"


def test_inject_with_class_constructor():
    """Test @inject decorator with class constructor."""
    store = InjectipyStore()
    store.register_value("service", "injected_service")

    class TestClass:
        @inject
        def __init__(self, service: str = Inject["service"]):
            self.service = service

    # Test constructor injection
    instance = TestClass()
    assert instance.service == "injected_service"


def test_inject_call_returns_self():
    """Test that calling Inject instance returns itself."""
    inject_instance = Inject["test_key"]
    result = inject_instance()
    assert result is inject_instance


def test_inject_different_key_types():
    """Test Inject with different key types."""
    # String key
    string_inject = Inject["string_key"]
    assert string_inject.get_inject_key() == "string_key"

    # Integer key
    int_inject = Inject[42]
    assert int_inject.get_inject_key() == 42

    # Type key
    type_inject = Inject[str]
    assert type_inject.get_inject_key() is str

    # Complex object key
    class CustomKey:
        pass

    obj_inject = Inject[CustomKey]
    assert obj_inject.get_inject_key() is CustomKey


def test_resolver_with_varargs_rejected(store: InjectipyStore):
    """Test that resolvers with *args are rejected."""

    def bad_resolver(*args):
        return "result"

    with pytest.raises(ValueError, match="has unsupported parameter kind VAR_POSITIONAL"):
        store.register_resolver("bad", bad_resolver)


def test_resolver_with_kwargs_rejected(store: InjectipyStore):
    """Test that resolvers with **kwargs are rejected."""

    def bad_resolver(**kwargs):
        return "result"

    with pytest.raises(ValueError, match="has unsupported parameter kind VAR_KEYWORD"):
        store.register_resolver("bad", bad_resolver)


def test_resolver_with_both_varargs_and_kwargs_rejected(store: InjectipyStore):
    """Test that resolvers with both *args and **kwargs are rejected."""

    def bad_resolver(*args, **kwargs):
        return "result"

    with pytest.raises(ValueError, match="has unsupported parameter kind VAR_POSITIONAL"):
        store.register_resolver("bad", bad_resolver)


def test_deep_dependency_chain(store: InjectipyStore):
    """Test resolution of deep dependency chains."""

    # Create a chain: A -> B -> C -> D -> E
    def resolver_e():
        return "E"

    def resolver_d(e=Inject["e"]):
        return f"D({e})"

    def resolver_c(d=Inject["d"]):
        return f"C({d})"

    def resolver_b(c=Inject["c"]):
        return f"B({c})"

    def resolver_a(b=Inject["b"]):
        return f"A({b})"

    # Register in order
    store.register_resolver("e", resolver_e)
    store.register_resolver("d", resolver_d)
    store.register_resolver("c", resolver_c)
    store.register_resolver("b", resolver_b)
    store.register_resolver("a", resolver_a)

    result = store["a"]
    assert result == "A(B(C(D(E))))"


def test_diamond_dependency_pattern(store: InjectipyStore):
    """Test diamond dependency pattern: A depends on B,C and B,C both depend on D."""

    def resolver_d():
        return "shared_D"

    def resolver_b(d=Inject["d"]):
        return f"B_uses_{d}"

    def resolver_c(d=Inject["d"]):
        return f"C_uses_{d}"

    def resolver_a(b=Inject["b"], c=Inject["c"]):
        return f"A_combines_{b}_and_{c}"

    store.register_resolver("d", resolver_d)
    store.register_resolver("b", resolver_b)
    store.register_resolver("c", resolver_c)
    store.register_resolver("a", resolver_a)

    result = store["a"]
    assert result == "A_combines_B_uses_shared_D_and_C_uses_shared_D"


def test_mixed_value_and_resolver_dependencies(store: InjectipyStore):
    """Test mixing values and resolvers in dependency chains."""
    # Mix of values and resolvers
    store.register_value("config_value", "production")

    def service_factory(config=Inject["config_value"]):
        return f"Service_{config}"

    def repository_factory(service=Inject["service"]):
        return f"Repository_with_{service}"

    store.register_resolver("service", service_factory)
    store.register_resolver("repository", repository_factory)

    result = store["repository"]
    assert result == "Repository_with_Service_production"


def test_optional_dependencies_with_defaults(store: InjectipyStore):
    """Test resolvers with optional dependencies that have defaults."""
    # Only register some dependencies
    store.register_value("required_dep", "required_value")

    def resolver_with_optional(required=Inject["required_dep"], optional_param="param_default"):
        return f"{required}|{optional_param}"

    store.register_resolver("with_optional", resolver_with_optional)
    result = store["with_optional"]
    assert result == "required_value|param_default"


def test_resolver_exception_propagation(store: InjectipyStore):
    """Test that exceptions in resolvers are properly propagated."""

    def failing_resolver():
        raise ValueError("Resolver failed intentionally")

    store.register_resolver("failing", failing_resolver)

    with pytest.raises(ValueError, match="Resolver failed intentionally"):
        store["failing"]


def test_nested_resolver_exception_propagation(store: InjectipyStore):
    """Test exception propagation through nested resolvers."""

    def failing_base():
        raise RuntimeError("Base resolver failed")

    def dependent_resolver(base=Inject["base"]):
        return f"Dependent: {base}"

    store.register_resolver("base", failing_base)
    store.register_resolver("dependent", dependent_resolver)

    with pytest.raises(RuntimeError, match="Base resolver failed"):
        store["dependent"]
