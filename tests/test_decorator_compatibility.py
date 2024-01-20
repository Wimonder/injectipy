"""Tests for @inject compatibility with other Python decorators."""

from contextlib import contextmanager
from functools import lru_cache, wraps

import pytest

from injectipy import DependencyNotFoundError, DependencyScope, Inject, inject


@pytest.fixture
def test_scope():
    """Provide a scope with test dependencies."""
    scope = DependencyScope()
    scope.register_value("service", "injected_service")
    scope.register_value("dep1", "injected_dep1")
    scope.register_value("dep2", "injected_dep2")
    return scope


# =============================================================================
# DECORATOR ORDER TESTS
# =============================================================================


def test_contextmanager_then_inject(test_scope):
    """Test @contextmanager then @inject (correct order)."""
    with test_scope:

        @contextmanager
        @inject
        def context_func(name: str, service: str = Inject["service"]) -> str:
            try:
                yield f"context: {name} + {service}"
            finally:
                pass

        with context_func("test") as resource:
            assert resource == "context: test + injected_service"


def test_inject_then_contextmanager(test_scope):
    """Test @inject then @contextmanager (incorrect order - should fail)."""
    with test_scope:

        @inject
        @contextmanager
        def context_func(name: str, service: str = Inject["service"]) -> str:
            try:
                yield f"context: {name} + {service}"
            finally:
                pass

        with context_func("test") as resource:
            # When @inject is applied first, it doesn't work properly
            assert "Inject object" in str(resource)


def test_lru_cache_then_inject(test_scope):
    """Test @lru_cache then @inject (correct order)."""
    with test_scope:

        @lru_cache(maxsize=2)
        @inject
        def cached_func(data: str, service: str = Inject["service"]) -> str:
            return f"cached: {data} + {service}"

        result1 = cached_func("test1")
        result2 = cached_func("test1")  # Should be cached
        assert result1 == "cached: test1 + injected_service"
        assert result2 == "cached: test1 + injected_service"


def test_inject_then_lru_cache(test_scope):
    """Test @inject then @lru_cache (incorrect order - should fail)."""
    with test_scope:

        @inject
        @lru_cache(maxsize=2)
        def cached_func(data: str, service: str = Inject["service"]) -> str:
            return f"cached: {data} + {service}"

        result1 = cached_func("test1")
        result2 = cached_func("test1")  # Should be cached
        # When @inject is applied first, it doesn't work properly
        assert "Inject object" in str(result1)
        assert "Inject object" in str(result2)


def custom_decorator(func):
    """A custom decorator that adds metadata."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return f"custom_decorated({result})"

    wrapper.custom_meta = "added_by_decorator"
    return wrapper


def test_custom_then_inject(test_scope):
    """Test custom decorator then @inject (correct order)."""
    with test_scope:

        @custom_decorator
        @inject
        def func(data: str, service: str = Inject["service"]) -> str:
            return f"data={data}, service={service}"

        result = func("test")
        has_meta = hasattr(func, "custom_meta")
        assert result == "custom_decorated(data=test, service=injected_service)"
        assert has_meta is True


def test_inject_then_custom(test_scope):
    """Test @inject then custom decorator (incorrect order - should fail)."""
    with test_scope:

        @inject
        @custom_decorator
        def func(data: str, service: str = Inject["service"]) -> str:
            return f"data={data}, service={service}"

        result = func("test")
        has_meta = hasattr(func, "custom_meta")
        # When @inject is applied first, it doesn't work properly
        assert "Inject object" in str(result)
        assert has_meta is True


def test_property_then_inject(test_scope):
    """Test @property then @inject (correct order)."""
    with test_scope:

        class TestClass:
            def __init__(self):
                self._value = "base"

            @property
            @inject
            def computed_value(self, service: str = Inject["service"]) -> str:
                return f"property: {self._value} + {service}"

        obj = TestClass()
        assert obj.computed_value == "property: base + injected_service"


def test_inject_then_property(test_scope):
    """Test @inject then @property (incorrect order - should fail)."""
    with test_scope:

        class TestClass:
            def __init__(self):
                self._value = "base"

            @inject
            @property
            def computed_value(self, service: str = Inject["service"]) -> str:
                return f"property: {self._value} + {service}"

        obj = TestClass()
        # When @inject is applied first, it doesn't work properly
        assert "Inject object" in str(obj.computed_value)


# =============================================================================
# CLASSMETHOD AND STATICMETHOD TESTS
# =============================================================================


class TestClassmethodInteractions:
    """Test @inject with @classmethod in various combinations."""

    def test_inject_then_classmethod(self, test_scope):
        """Test @inject then @classmethod (correct order)."""
        with test_scope:

            class TestClass:
                @inject
                @classmethod
                def method(cls, data: str, service: str = Inject["service"]) -> str:
                    return f"classmethod: {cls.__name__}, {data}, {service}"

            result = TestClass.method("test")
            assert result == "classmethod: TestClass, test, injected_service"

    def test_classmethod_then_inject(self, test_scope):
        """Test @classmethod then @inject (works with thread-safe implementation)."""
        with test_scope:

            class TestClass:
                @classmethod
                @inject
                def method(cls, data: str, service: str = Inject["service"]) -> str:
                    return f"classmethod: {cls.__name__}, {data}, {service}"

            result = TestClass.method("test")
            # With the new thread-safe implementation, this actually works
            assert result == "classmethod: TestClass, test, injected_service"

    def test_classmethod_with_multiple_parameters(self, test_scope):
        """Test @classmethod with multiple injected parameters."""
        with test_scope:

            class TestClass:
                @inject
                @classmethod
                def method(cls, data: str, svc1: str = Inject["dep1"], svc2: str = Inject["dep2"]) -> str:
                    return f"class={cls.__name__}, data={data}, svc1={svc1}, svc2={svc2}"

            result = TestClass.method("test")
            assert result == "class=TestClass, data=test, svc1=injected_dep1, svc2=injected_dep2"

    def test_classmethod_with_keyword_only_params(self, test_scope):
        """Test @classmethod with keyword-only injected parameters."""
        with test_scope:

            class TestClass:
                @inject
                @classmethod
                def method(cls, data: str, *, service: str = Inject["service"], flag: bool = True) -> str:
                    return f"class={cls.__name__}, data={data}, service={service}, flag={flag}"

            result = TestClass.method("test")
            assert result == "class=TestClass, data=test, service=injected_service, flag=True"

    def test_classmethod_missing_dependency(self, test_scope):
        """Test @classmethod with missing dependency."""
        with test_scope:

            class TestClass:
                @inject
                @classmethod
                def method(cls, missing: str = Inject["nonexistent"]) -> str:
                    return f"class={cls.__name__}, missing={missing}"

            with pytest.raises(DependencyNotFoundError, match="Dependency 'nonexistent' not found"):
                TestClass.method()


class TestStaticmethodInteractions:
    """Test @inject with @staticmethod in various combinations."""

    def test_inject_then_staticmethod(self, test_scope):
        """Test @inject then @staticmethod (correct order)."""
        with test_scope:

            class TestClass:
                @inject
                @staticmethod
                def method(data: str, service: str = Inject["service"]) -> str:
                    return f"staticmethod: {data}, {service}"

            result = TestClass.method("test")
            assert result == "staticmethod: test, injected_service"

    def test_staticmethod_then_inject(self, test_scope):
        """Test @staticmethod then @inject (works with thread-safe implementation)."""
        with test_scope:

            class TestClass:
                @staticmethod
                @inject
                def method(data: str, service: str = Inject["service"]) -> str:
                    return f"staticmethod: {data}, {service}"

            result = TestClass.method("test")
            # With the new thread-safe implementation, this actually works
            assert result == "staticmethod: test, injected_service"

    def test_staticmethod_with_multiple_parameters(self, test_scope):
        """Test @staticmethod with multiple injected parameters."""
        with test_scope:

            class TestClass:
                @inject
                @staticmethod
                def method(data: str, svc1: str = Inject["dep1"], svc2: str = Inject["dep2"]) -> str:
                    return f"data={data}, svc1={svc1}, svc2={svc2}"

            result = TestClass.method("test")
            assert result == "data=test, svc1=injected_dep1, svc2=injected_dep2"

    def test_staticmethod_with_keyword_only_params(self, test_scope):
        """Test @staticmethod with keyword-only injected parameters."""
        with test_scope:

            class TestClass:
                @inject
                @staticmethod
                def method(data: str, *, service: str = Inject["service"], flag: bool = True) -> str:
                    return f"data={data}, service={service}, flag={flag}"

            result = TestClass.method("test")
            assert result == "data=test, service=injected_service, flag=True"

    def test_staticmethod_missing_dependency(self, test_scope):
        """Test @staticmethod with missing dependency."""
        with test_scope:

            class TestClass:
                @inject
                @staticmethod
                def method(missing: str = Inject["nonexistent"]) -> str:
                    return f"missing={missing}"

            with pytest.raises(DependencyNotFoundError, match="Dependency 'nonexistent' not found"):
                TestClass.method()


class TestComplexDecoratorInteractions:
    """Test complex decorator interaction scenarios."""

    def test_multiple_decorators_with_inject(self, test_scope):
        """Test @inject with multiple other decorators."""
        with test_scope:

            def timing_decorator(func):
                @wraps(func)
                def wrapper(*args, **kwargs):
                    result = func(*args, **kwargs)
                    return f"timed({result})"

                return wrapper

            def logging_decorator(func):
                @wraps(func)
                def wrapper(*args, **kwargs):
                    result = func(*args, **kwargs)
                    return f"logged({result})"

                return wrapper

            # Apply decorators in correct order: others first, then @inject
            @timing_decorator
            @logging_decorator
            @inject
            def multi_decorated_func(data: str, service: str = Inject["service"]) -> str:
                return f"data={data}, service={service}"

            result = multi_decorated_func("test")
            assert result == "timed(logged(data=test, service=injected_service))"

    def test_inheritance_with_decorated_methods(self, test_scope):
        """Test inheritance with injected class methods."""
        with test_scope:

            class BaseClass:
                @inject
                @classmethod
                def base_method(cls, service: str = Inject["dep1"]) -> str:
                    return f"base: {cls.__name__}, {service}"

            class DerivedClass(BaseClass):
                @inject
                @classmethod
                def derived_method(cls, service: str = Inject["dep2"]) -> str:
                    return f"derived: {cls.__name__}, {service}"

            # Test base method from derived class
            result1 = DerivedClass.base_method()
            assert result1 == "base: DerivedClass, injected_dep1"

            # Test derived method
            result2 = DerivedClass.derived_method()
            assert result2 == "derived: DerivedClass, injected_dep2"

    def test_decorator_preservation_of_metadata(self, test_scope):
        """Test that decorator combinations preserve function metadata."""
        with test_scope:

            @custom_decorator
            @inject
            def documented_function(service: str = Inject["service"]) -> str:
                """This function has documentation."""
                return f"Result: {service}"

            # Check that metadata is preserved
            assert documented_function.__doc__ == "This function has documentation."
            assert hasattr(documented_function, "custom_meta")
            assert documented_function.custom_meta == "added_by_decorator"
