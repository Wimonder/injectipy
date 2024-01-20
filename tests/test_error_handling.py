"""Error handling and validation tests for injectipy."""

import pytest

from injectipy import (
    CircularDependencyError,
    DependencyNotFoundError,
    DependencyScope,
    DuplicateRegistrationError,
    Inject,
    InvalidStoreOperationError,
    inject,
)


@pytest.fixture
def test_scope():
    """Provide a clean scope for each test."""
    return DependencyScope()


# =============================================================================
# CIRCULAR DEPENDENCY TESTS
# =============================================================================


def test_simple_circular_dependency(test_scope: DependencyScope):
    """Test detection of simple circular dependency (A -> B -> A)."""

    def service_a(b=Inject["service_b"]):
        return f"A depends on {b}"

    def service_b(a=Inject["service_a"]):
        return f"B depends on {a}"

    test_scope.register_resolver("service_a", service_a)

    with pytest.raises(CircularDependencyError, match="Circular dependency"):
        test_scope.register_resolver("service_b", service_b)


def test_self_circular_dependency(test_scope: DependencyScope):
    """Test detection of self-referencing circular dependency (A -> A)."""

    def service_a(a=Inject["service_a"]):
        return f"A depends on {a}"

    with pytest.raises(CircularDependencyError, match="Circular dependency"):
        test_scope.register_resolver("service_a", service_a)


def test_complex_circular_dependency(test_scope: DependencyScope):
    """Test detection of complex circular dependency (A -> B -> C -> A)."""

    def service_a(b=Inject["service_b"]):
        return f"A depends on {b}"

    def service_b(c=Inject["service_c"]):
        return f"B depends on {c}"

    def service_c(a=Inject["service_a"]):
        return f"C depends on {a}"

    test_scope.register_resolver("service_a", service_a)
    test_scope.register_resolver("service_b", service_b)

    with pytest.raises(CircularDependencyError, match="Circular dependency"):
        test_scope.register_resolver("service_c", service_c)


def test_no_circular_dependency_with_values(test_scope: DependencyScope):
    """Test that values don't create circular dependencies."""
    with test_scope:
        test_scope.register_value("base_value", "foundation")

        def service_a(base=Inject["base_value"]):
            return f"A uses {base}"

        def service_b(a=Inject["service_a"], base=Inject["base_value"]):
            return f"B uses {a} and {base}"

        # Should not raise circular dependency error
        test_scope.register_resolver("service_a", service_a)
        test_scope.register_resolver("service_b", service_b)

        assert test_scope["service_b"] == "B uses A uses foundation and foundation"


def test_valid_dependency_chain(test_scope: DependencyScope):
    """Test valid linear dependency chain (A -> B -> C)."""
    with test_scope:
        test_scope.register_value("base", "foundation")

        def service_c(base=Inject["base"]):
            return f"C uses {base}"

        def service_b(c=Inject["service_c"]):
            return f"B uses {c}"

        def service_a(b=Inject["service_b"]):
            return f"A uses {b}"

        test_scope.register_resolver("service_c", service_c)
        test_scope.register_resolver("service_b", service_b)
        test_scope.register_resolver("service_a", service_a)

        result = test_scope["service_a"]
        assert result == "A uses B uses C uses foundation"


def test_mixed_inject_dependencies(test_scope: DependencyScope):
    """Test resolvers with mixed inject and regular dependencies."""
    with test_scope:
        test_scope.register_value("config", {"env": "test"})

        def database_service(config=Inject["config"]):
            return f"Database({config['env']})"

        def auth_service(db=Inject["database"], fallback="guest"):
            return f"Auth({db}, fallback={fallback})"

        test_scope.register_resolver("database", database_service)
        test_scope.register_resolver("auth", auth_service)

        result = test_scope["auth"]
        assert result == "Auth(Database(test), fallback=guest)"


def test_circular_dependency_path_detection(test_scope: DependencyScope):
    """Test detailed circular dependency path detection."""

    def service_a(b=Inject["service_b"]):
        return f"A -> {b}"

    def service_b(c=Inject["service_c"]):
        return f"B -> {c}"

    def service_c(d=Inject["service_d"]):
        return f"C -> {d}"

    def service_d(a=Inject["service_a"]):  # Creates: A -> B -> C -> D -> A
        return f"D -> {a}"

    test_scope.register_resolver("service_a", service_a)
    test_scope.register_resolver("service_b", service_b)
    test_scope.register_resolver("service_c", service_c)

    with pytest.raises(CircularDependencyError, match="Circular dependency"):
        test_scope.register_resolver("service_d", service_d)


def test_dependency_path_with_nonexistent_keys(test_scope: DependencyScope):
    """Test dependency path detection with nonexistent keys."""
    with test_scope:

        def service_a(nonexistent=Inject["does_not_exist"]):
            return f"A uses {nonexistent}"

        # Should not raise circular dependency error during registration
        test_scope.register_resolver("service_a", service_a)

        # Should fall back to Inject object when dependency is missing
        result = test_scope["service_a"]
        assert "Inject object" in str(result)


# =============================================================================
# MISSING DEPENDENCY TESTS
# =============================================================================


def test_inject_decorator_runtime_error_chaining(test_scope: DependencyScope):
    """Test that DependencyNotFoundError chains the original KeyError properly."""

    @inject
    def func_with_missing_dep(missing=Inject["nonexistent"]):
        return missing

    try:
        func_with_missing_dep()
        raise AssertionError("Should have raised DependencyNotFoundError")
    except DependencyNotFoundError as e:
        # Check that the original DependencyNotFoundError is chained
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, DependencyNotFoundError)
        assert "Dependency 'nonexistent' not found" in str(e)


def test_resolver_with_missing_inject_dependency(test_scope: DependencyScope):
    """Test resolver that depends on missing injected dependency."""
    with test_scope:

        def dependent_resolver(missing=Inject["nonexistent"]):
            return f"depends on {missing}"

        # Registration should succeed (forward references allowed)
        test_scope.register_resolver("dependent", dependent_resolver)

        # Resolution should fall back to Inject object when dependency is missing
        result = test_scope["dependent"]
        assert "Inject object" in str(result)


def test_resolver_exception_propagation(test_scope: DependencyScope):
    """Test that exceptions in resolvers propagate correctly."""
    with test_scope:

        def failing_resolver():
            raise ValueError("Resolver failed")

        test_scope.register_resolver("failing", failing_resolver)

        with pytest.raises(ValueError, match="Resolver failed"):
            _ = test_scope["failing"]


def test_nested_resolver_exception_propagation(test_scope: DependencyScope):
    """Test exception propagation through nested resolver calls."""
    with test_scope:

        def failing_base():
            raise RuntimeError("Base resolver failed")

        def dependent_resolver(base=Inject["base"]):
            return f"depends on {base}"

        test_scope.register_resolver("base", failing_base)
        test_scope.register_resolver("dependent", dependent_resolver)

        with pytest.raises(RuntimeError, match="Base resolver failed"):
            _ = test_scope["dependent"]


# =============================================================================
# VALIDATION ERROR TESTS - Removed for simplicity
# =============================================================================


def test_duplicate_key_registration(test_scope: DependencyScope):
    """Test that duplicate key registration raises ValueError."""
    test_scope.register_value("duplicate", "first")

    with pytest.raises(DuplicateRegistrationError, match="Key 'duplicate' is already registered"):
        test_scope.register_value("duplicate", "second")

    with pytest.raises(DuplicateRegistrationError, match="Key 'duplicate' is already registered"):
        test_scope.register_resolver("duplicate", lambda: "resolver")


def test_setitem_not_implemented(test_scope: DependencyScope):
    """Test that direct assignment to store raises NotImplementedError."""
    with pytest.raises(InvalidStoreOperationError, match="Invalid operation"):
        test_scope["key"] = "value"


# =============================================================================
# EDGE CASE ERROR HANDLING
# =============================================================================


def test_inject_decorator_restores_defaults(test_scope: DependencyScope):
    """Test that @inject restores function defaults after exception."""
    with test_scope:
        test_scope.register_value("service", "injected")

        @inject
        def func_that_raises(data, service=Inject["service"]):
            if data == "error":
                raise ValueError("Intentional error")
            return f"{data}: {service}"

        # Normal call should work
        result = func_that_raises("normal")
        assert result == "normal: injected"

        # Exception should be raised and defaults should be restored
        with pytest.raises(ValueError, match="Intentional error"):
            func_that_raises("error")

        # Should still work after exception
        result = func_that_raises("after_error")
        assert result == "after_error: injected"


def test_resolver_with_inject_and_defaults(test_scope: DependencyScope):
    """Test resolver with both Inject and regular default parameters."""
    with test_scope:
        test_scope.register_value("injected", "from_store")

        def mixed_resolver(injected_param=Inject["injected"], regular_param="default"):
            return f"injected={injected_param}, regular={regular_param}"

        test_scope.register_resolver("mixed", mixed_resolver)

        result = test_scope["mixed"]
        assert result == "injected=from_store, regular=default"


def test_injection_during_exception(test_scope: DependencyScope):
    """Test that injection works properly during exception handling."""
    with test_scope:
        test_scope.register_value("logger", "error_logger")

        @inject
        def error_handler(error_type, logger=Inject["logger"]):
            return f"Handling {error_type} with {logger}"

        try:
            raise ValueError("test error")
        except ValueError as e:
            result = error_handler(type(e).__name__)
            assert result == "Handling ValueError with error_logger"
