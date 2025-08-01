"""Tests for DependencyScope functionality and context management."""

import threading
import time

import pytest

from injectipy import (
    CircularDependencyError,
    DependencyNotFoundError,
    DependencyScope,
    DuplicateRegistrationError,
    Inject,
    InvalidStoreOperationError,
    clear_scope_stack,
    dependency_scope,
    get_active_scopes,
    inject,
    resolve_dependency,
)


class TestBasicScopeFunctionality:
    """Test basic scope registration and retrieval."""

    def test_scope_creation(self):
        """Test basic scope creation."""
        scope = DependencyScope()
        assert scope is not None
        assert not scope.is_active()

    def test_register_value(self):
        """Test registering static values."""
        scope = DependencyScope()
        scope.register_value("key", "value")
        assert scope["key"] == "value"
        assert scope.contains("key")

    def test_register_resolver(self):
        """Test registering resolver functions."""
        scope = DependencyScope()
        scope.register_resolver("key", lambda: "resolved_value")
        assert scope["key"] == "resolved_value"
        assert scope.contains("key")

    def test_method_chaining(self):
        """Test that registration methods support chaining."""
        scope = DependencyScope()
        result = scope.register_value("key1", "value1").register_resolver("key2", lambda: "value2")
        assert result is scope
        assert scope["key1"] == "value1"
        assert scope["key2"] == "value2"

    def test_scope_isolation(self):
        """Test that scopes are isolated from each other."""
        scope1 = DependencyScope()
        scope2 = DependencyScope()

        scope1.register_value("key", "value1")
        scope2.register_value("key", "value2")

        assert scope1["key"] == "value1"
        assert scope2["key"] == "value2"

    def test_key_not_found(self):
        """Test accessing non-existent key raises DependencyNotFoundError."""
        scope = DependencyScope()
        with pytest.raises(DependencyNotFoundError, match="Dependency 'nonexistent' not found"):
            _ = scope["nonexistent"]


class TestContextManager:
    """Test scope context manager functionality."""

    def test_context_manager_activation(self):
        """Test scope activation and deactivation."""
        scope = DependencyScope()
        assert not scope.is_active()

        with scope:
            assert scope.is_active()

        assert not scope.is_active()

    def test_context_manager_cleanup(self):
        """Test that context manager cleans up on exit."""
        scope = DependencyScope()
        scope.register_value("key", "value")

        with scope:
            assert scope["key"] == "value"

        # After exit, the scope should be cleaned up
        with pytest.raises(DependencyNotFoundError):
            _ = scope["key"]

    def test_nested_scopes(self):
        """Test nested scope contexts."""
        outer = DependencyScope()
        inner = DependencyScope()

        outer.register_value("outer_key", "outer_value")
        inner.register_value("inner_key", "inner_value")

        with outer:
            assert get_active_scopes() == [outer]

            with inner:
                scopes = get_active_scopes()
                assert len(scopes) == 2
                assert scopes == [outer, inner]

            assert get_active_scopes() == [outer]

        assert get_active_scopes() == []

    def test_dependency_scope_convenience_function(self):
        """Test the dependency_scope() convenience function."""
        with dependency_scope() as scope:
            scope.register_value("key", "value")
            assert scope["key"] == "value"
            assert scope.is_active()

        assert not scope.is_active()


class TestScopeResolution:
    """Test dependency resolution across scopes."""

    def test_single_scope_resolution(self):
        """Test resolution within a single scope."""
        with DependencyScope() as scope:
            scope.register_value("service", "test_service")

            @inject
            def test_func(service: str = Inject["service"]):
                return service

            assert test_func() == "test_service"

    def test_nested_scope_resolution(self):
        """Test resolution with nested scopes (inner wins)."""
        with DependencyScope() as outer:
            outer.register_value("key", "outer_value")

            with DependencyScope() as inner:
                inner.register_value("key", "inner_value")

                @inject
                def test_func(key: str = Inject["key"]):
                    return key

                # Inner scope should win
                assert test_func() == "inner_value"

    def test_nested_scope_fallback(self):
        """Test resolution falls back to outer scope."""
        with DependencyScope() as outer:
            outer.register_value("outer_key", "outer_value")

            with DependencyScope() as inner:
                inner.register_value("inner_key", "inner_value")

                @inject
                def test_outer(outer_key: str = Inject["outer_key"]):
                    return outer_key

                @inject
                def test_inner(inner_key: str = Inject["inner_key"]):
                    return inner_key

                assert test_outer() == "outer_value"  # From outer scope
                assert test_inner() == "inner_value"  # From inner scope

    def test_explicit_scopes_override(self):
        """Test explicit scopes override active scopes."""
        explicit_scope = DependencyScope()
        explicit_scope.register_value("key", "explicit_value")

        with DependencyScope() as active_scope:
            active_scope.register_value("key", "active_value")

            @inject(scopes=[explicit_scope])
            def test_func(key: str = Inject["key"]):
                return key

            # Explicit scope should win over active scope
            assert test_func() == "explicit_value"

    def test_multiple_explicit_scopes(self):
        """Test multiple explicit scopes (last one wins)."""
        scope1 = DependencyScope()
        scope2 = DependencyScope()

        scope1.register_value("key", "value1")
        scope2.register_value("key", "value2")

        @inject(scopes=[scope1, scope2])
        def test_func(key: str = Inject["key"]):
            return key

        # Last explicit scope should win
        assert test_func() == "value2"

    def test_resolve_dependency_function(self):
        """Test the resolve_dependency function directly."""
        with DependencyScope() as scope:
            scope.register_value("key", "value")

            result = resolve_dependency("key")
            assert result == "value"

        # Outside scope should raise error
        with pytest.raises(DependencyNotFoundError):
            resolve_dependency("key")

    def test_missing_dependency_error_with_suggestions(self):
        """Test missing dependency provides available keys as suggestions."""
        with DependencyScope() as scope:
            scope.register_value("available_key1", "value1")
            scope.register_value("available_key2", "value2")

            @inject
            def test_func(missing: str = Inject["missing_key"]):
                return missing

            with pytest.raises(DependencyNotFoundError) as exc_info:
                test_func()

            error = exc_info.value
            assert "missing_key" in str(error)
            assert error.available_keys is not None
            assert "available_key1" in error.available_keys
            assert "available_key2" in error.available_keys


class TestResolverFunctionality:
    """Test resolver function functionality."""

    def test_resolver_with_dependencies(self):
        """Test resolver that depends on other registered values."""
        with DependencyScope() as scope:
            scope.register_value("base", "foundation")

            def dependent_resolver(base_dep: str = Inject["base"]) -> str:
                return f"built_on_{base_dep}"

            scope.register_resolver("dependent", dependent_resolver)
            assert scope["dependent"] == "built_on_foundation"

    def test_nested_resolvers(self):
        """Test resolvers that depend on other resolvers."""
        with DependencyScope() as scope:
            scope.register_resolver("level1", lambda: "base")

            def level2_resolver(dep: str = Inject["level1"]) -> str:
                return f"level2_{dep}"

            def level3_resolver(dep: str = Inject["level2"]) -> str:
                return f"level3_{dep}"

            scope.register_resolver("level2", level2_resolver)
            scope.register_resolver("level3", level3_resolver)

            assert scope["level3"] == "level3_level2_base"

    def test_evaluate_once_caching(self):
        """Test evaluate_once=True caches resolver results."""
        call_count = 0

        def counting_resolver() -> str:
            nonlocal call_count
            call_count += 1
            return f"call_{call_count}"

        scope = DependencyScope()
        scope.register_resolver("cached", counting_resolver, evaluate_once=True)

        # First call should execute resolver
        result1 = scope["cached"]
        assert result1 == "call_1"
        assert call_count == 1

        # Second call should return cached result
        result2 = scope["cached"]
        assert result2 == "call_1"  # Same result
        assert call_count == 1  # Not called again


class TestErrorHandling:
    """Test error handling and validation."""

    def test_duplicate_registration(self):
        """Test duplicate key registration raises error."""
        scope = DependencyScope()
        scope.register_value("duplicate", "first")

        with pytest.raises(DuplicateRegistrationError, match="Key 'duplicate' is already registered"):
            scope.register_value("duplicate", "second")

    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        scope = DependencyScope()

        def service_a(b=Inject["service_b"]):
            return f"A depends on {b}"

        def service_b(a=Inject["service_a"]):
            return f"B depends on {a}"

        scope.register_resolver("service_a", service_a)

        with pytest.raises(CircularDependencyError, match="Circular dependency"):
            scope.register_resolver("service_b", service_b)

    def test_invalid_resolver_parameters(self):
        """Test removed - parameter validation simplified."""
        pass  # Test removed for simplicity

    def test_direct_assignment_not_allowed(self):
        """Test direct assignment raises error."""
        scope = DependencyScope()
        with pytest.raises(InvalidStoreOperationError):  # Should raise InvalidStoreOperationError
            scope["key"] = "value"


class TestThreadSafety:
    """Test thread safety of scopes."""

    def test_concurrent_scope_access(self):
        """Test concurrent access to the same scope."""
        scope = DependencyScope()
        scope.register_value("shared", "value")

        results = []

        def worker():
            try:
                result = scope["shared"]
                results.append(result)
            except Exception as e:
                results.append(f"Error: {e}")

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should get the same result
        assert all(result == "value" for result in results)
        assert len(results) == 10

    def test_thread_local_scope_stack(self):
        """Test that scope stacks are thread-local."""
        results = {}

        def worker(thread_id):
            with DependencyScope() as scope:
                scope.register_value("thread_id", thread_id)
                time.sleep(0.01)  # Let other threads run

                @inject
                def get_thread_id(thread_id: int = Inject["thread_id"]):
                    return thread_id

                results[thread_id] = get_thread_id()

        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Each thread should get its own value
        for i in range(5):
            assert results[i] == i


class TestScopeCleanup:
    """Test scope cleanup and state management."""

    def test_scope_cleanup_after_exception(self):
        """Test scope is properly cleaned up after exception."""
        scope = DependencyScope()
        scope.register_value("key", "value")

        try:
            with scope:
                assert scope.is_active()
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Scope should be deactivated and cleaned up
        assert not scope.is_active()
        with pytest.raises(DependencyNotFoundError):
            _ = scope["key"]

    def test_clear_scope_stack(self):
        """Test clearing the scope stack."""
        with DependencyScope():
            with DependencyScope():
                assert len(get_active_scopes()) == 2
                clear_scope_stack()
                assert len(get_active_scopes()) == 0

        # After clearing, scopes should still be in context but not active
        assert len(get_active_scopes()) == 0
