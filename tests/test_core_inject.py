"""Core @inject decorator functionality tests."""

import pytest

from injectipy import DependencyNotFoundError, DependencyScope, Inject, inject


def test_inject_basic_function(basic_scope):
    """Test basic @inject decorator on a simple function."""
    with basic_scope:

        @inject
        def my_function(name: str, service: str = Inject["service"]) -> str:
            return f"Hello {name}, service: {service}"

        result = my_function("Alice")
        assert result == "Hello Alice, service: injected_service"


def test_inject_overwrite_defaults(basic_scope):
    """Test that explicitly passed arguments override injection."""
    with basic_scope:

        @inject
        def my_function(name: str, service: str = Inject["service"]) -> str:
            return f"Hello {name}, service: {service}"

        result = my_function("Alice", "custom_service")
        assert result == "Hello Alice, service: custom_service"


def test_inject_class_constructor(basic_scope):
    """Test @inject on class constructors."""
    with basic_scope:

        class MyClass:
            @inject
            def __init__(self, service: str = Inject["service"]):
                self.service = service

        obj = MyClass()
        assert obj.service == "injected_service"


def test_inject_class_methods(basic_scope):
    """Test @inject on regular class methods."""
    with basic_scope:

        class MyClass:
            @inject
            def method(self, data: str, service: str = Inject["service"]) -> str:
                return f"Method: {data} with {service}"

        obj = MyClass()
        result = obj.method("test")
        assert result == "Method: test with injected_service"


def test_inject_no_defaults():
    """Test @inject decorator on function with no Inject defaults."""

    @inject
    def regular_function(name: str, value: str = "default") -> str:
        return f"{name}: {value}"

    result = regular_function("test")
    assert result == "test: default"


def test_inject_no_inject_defaults():
    """Test @inject when no parameters have Inject defaults."""

    @inject
    def no_inject_function(a: str, b: str = "default") -> str:
        return f"{a}, {b}"

    result = no_inject_function("hello")
    assert result == "hello, default"


def test_inject_missing_dependency():
    """Test @inject with missing dependency raises proper error."""

    @inject
    def func_with_missing_dep(name: str, missing: str = Inject["nonexistent"]) -> str:
        return f"{name}: {missing}"

    with pytest.raises(DependencyNotFoundError, match="Dependency 'nonexistent' not found"):
        func_with_missing_dep("test")


def test_inject_different_key_types():
    """Test @inject with different key types (string, type)."""
    with DependencyScope() as scope:
        scope.register_value("string_key", "string_value")
        scope.register_value(int, 42)

        @inject
        def func_with_type_keys(str_dep: str = Inject["string_key"], int_dep: int = Inject[int]) -> str:
            return f"str={str_dep}, int={int_dep}"

        result = func_with_type_keys()
        assert result == "str=string_value, int=42"


def test_inject_call_returns_self():
    """Test that Inject[key]() returns the Inject object (for type compatibility)."""
    inject_obj = Inject["test_key"]
    result = inject_obj()
    assert result is inject_obj


def test_inject_preserves_function_metadata(basic_scope):
    """Test that @inject preserves function name, docstring, etc."""
    with basic_scope:

        @inject
        def documented_function(service: str = Inject["service"]) -> str:
            """This function has documentation."""
            return f"Result: {service}"

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This function has documentation."


def test_inject_multiple_dependencies():
    """Test @inject with multiple injected parameters."""
    with DependencyScope() as scope:
        scope.register_value("dep1", "value1")
        scope.register_value("dep2", "value2")
        scope.register_value("dep3", "value3")

        @inject
        def multi_inject(a: str, b: str = Inject["dep1"], c: str = Inject["dep2"], d: str = Inject["dep3"]) -> str:
            return f"a={a}, b={b}, c={c}, d={d}"

        result = multi_inject("manual")
        assert result == "a=manual, b=value1, c=value2, d=value3"
