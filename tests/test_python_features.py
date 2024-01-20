"""Tests for @inject with advanced Python language features."""

import asyncio
import gc
import weakref
from collections import namedtuple
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial

import pytest

from injectipy import DependencyScope, Inject, inject


@pytest.fixture
def test_scope():
    """Provide a clean scope with test dependencies."""
    scope = DependencyScope()
    scope.register_value("service", "injected_service")
    scope.register_value("dep1", "injected_dep1")
    scope.register_value("dep2", "injected_dep2")
    scope.register_value("config", {"setting": "value"})
    return scope


# =============================================================================
# ASYNC/AWAIT SUPPORT
# =============================================================================


def test_async_function(test_scope):
    """Test @inject with async functions."""
    with test_scope:

        @inject
        async def async_function(data: str, service: str = Inject["service"]) -> str:
            await asyncio.sleep(0.001)  # Minimal async operation
            return f"async result: {data} with {service}"

        async def run_test():
            result = await async_function("test_data")
            return result

        result = asyncio.run(run_test())
        assert result == "async result: test_data with injected_service"


def test_async_method(test_scope):
    """Test @inject with async class methods."""
    with test_scope:

        class AsyncService:
            @inject
            async def process(self, data: str, service: str = Inject["service"]) -> str:
                await asyncio.sleep(0.001)
                return f"async method: {data} with {service}"

        async def run_test():
            service = AsyncService()
            result = await service.process("test")
            return result

        result = asyncio.run(run_test())
        assert result == "async method: test with injected_service"


def test_async_generator(test_scope):
    """Test @inject with async generators."""
    with test_scope:

        @inject
        async def async_generator(count: int, service: str = Inject["service"]):
            for i in range(count):
                await asyncio.sleep(0.001)
                yield f"async_item_{i} with {service}"

        async def run_test():
            results = []
            async for item in async_generator(3):
                results.append(item)
            return results

        results = asyncio.run(run_test())
        expected = [
            "async_item_0 with injected_service",
            "async_item_1 with injected_service",
            "async_item_2 with injected_service",
        ]
        assert results == expected


# =============================================================================
# GENERATORS
# =============================================================================


def test_generator_function(test_scope):
    """Test @inject with generator functions."""
    with test_scope:

        @inject
        def generator_function(count: int, service: str = Inject["service"]):
            for i in range(count):
                yield f"item_{i} with {service}"

        results = list(generator_function(3))

        expected = ["item_0 with injected_service", "item_1 with injected_service", "item_2 with injected_service"]
        assert results == expected


# =============================================================================
# DATACLASSES
# =============================================================================


def test_dataclass_post_init(test_scope):
    """Test @inject with dataclass __post_init__."""
    with test_scope:

        @dataclass
        class InjectedDataClass:
            name: str
            processed_name: str = None

            @inject
            def __post_init__(self, service: str = Inject["service"]):
                self.processed_name = f"{self.name} processed by {service}"

        obj = InjectedDataClass("test")
        assert obj.processed_name == "test processed by injected_service"


# =============================================================================
# SPECIAL METHODS / OPERATORS
# =============================================================================


def test_special_methods(test_scope):
    """Test @inject with various special methods."""
    with test_scope:

        class SpecialMethodsClass:
            def __init__(self, value: str):
                self.value = value

            @inject
            def __str__(self, service: str = Inject["service"]) -> str:
                return f"str: {self.value} with {service}"

            @inject
            def __repr__(self, service: str = Inject["dep1"]) -> str:
                return f"repr: {self.value} with {service}"

            @inject
            def __len__(self, service: str = Inject["service"]) -> int:
                return len(f"{self.value}_{service}")

            @inject
            def __bool__(self, service: str = Inject["service"]) -> bool:
                return len(f"{self.value}_{service}") > 10

        obj = SpecialMethodsClass("test")

        assert str(obj) == "str: test with injected_service"
        assert repr(obj) == "repr: test with injected_dep1"
        assert len(obj) == len("test_injected_service")
        assert bool(obj) is True  # "test_injected_service" is > 10 chars


def test_operator_injection(test_scope):
    """Test @inject with operator overloading."""
    with test_scope:

        class InjectableOperator:
            def __init__(self, value: str):
                self.value = value

            @inject
            def __add__(self, other, service: str = Inject["dep1"]) -> str:
                return f"add: {self.value} + {other} (with {service})"

            @inject
            def __mul__(self, other, service: str = Inject["dep2"]) -> str:
                return f"mul: {self.value} * {other} (with {service})"

        obj = InjectableOperator("base")
        add_result = obj + "other"
        mul_result = obj * 5

        assert add_result == "add: base + other (with injected_dep1)"
        assert mul_result == "mul: base * 5 (with injected_dep2)"


# =============================================================================
# NAMEDTUPLES AND BUILT-IN TYPES
# =============================================================================


def test_namedtuple_injection(test_scope):
    """Test @inject with namedtuple methods."""
    with test_scope:
        Point = namedtuple("Point", ["x", "y"])

        # Add an injected method to the namedtuple class
        def injected_distance(self, service: str = Inject["service"]) -> str:
            return f"distance calculation with {service}: {self.x**2 + self.y**2}"

        Point.distance = inject(injected_distance)

        point = Point(3, 4)
        result = point.distance()

        assert result == "distance calculation with injected_service: 25"


# =============================================================================
# CONTEXT MANAGERS
# =============================================================================


def test_context_manager_injection(test_scope):
    """Test @inject with context managers."""
    with test_scope:

        @contextmanager
        @inject
        def injected_context(resource_name: str, service: str = Inject["service"]):
            try:
                yield f"context_resource: {resource_name} + {service}"
            finally:
                pass

        with injected_context("test_resource") as resource:
            result = f"used {resource}"

        assert result == "used context_resource: test_resource + injected_service"


# =============================================================================
# INHERITANCE AND CLASS HIERARCHIES
# =============================================================================


def test_injection_with_multiple_inheritance(test_scope):
    """Test @inject with multiple inheritance."""
    with test_scope:

        class BaseA:
            @inject
            def method_a(self, service: str = Inject["dep1"]) -> str:
                return f"method_a with {service}"

        class BaseB:
            @inject
            def method_b(self, service: str = Inject["dep2"]) -> str:
                return f"method_b with {service}"

        class Derived(BaseA, BaseB):
            @inject
            def method_c(self, service: str = Inject["service"]) -> str:
                return f"method_c with {service}"

        obj = Derived()

        assert obj.method_a() == "method_a with injected_dep1"
        assert obj.method_b() == "method_b with injected_dep2"
        assert obj.method_c() == "method_c with injected_service"


def test_injection_with_nested_classes(test_scope):
    """Test @inject with nested class definitions."""
    with test_scope:

        class Outer:
            def __init__(self, value: str):
                self.value = value

            class Nested:
                @inject
                def nested_method(self, data: str, service: str = Inject["dep1"]) -> str:
                    return f"nested: {data} with {service}"

            @inject
            def outer_method(self, service: str = Inject["dep2"]) -> str:
                nested = self.Nested()
                nested_result = nested.nested_method("test")
                return f"outer: {self.value} with {service}, nested: {nested_result}"

        obj = Outer("outer_value")
        result = obj.outer_method()

        assert "outer: outer_value with injected_dep2" in result
        assert "nested: test with injected_dep1" in result


# =============================================================================
# RECURSIVE AND COMPLEX PATTERNS
# =============================================================================


def test_recursive_injection(test_scope):
    """Test @inject with recursive function calls."""
    with test_scope:

        @inject
        def factorial(n: int, service: str = Inject["service"]) -> str:
            if n <= 1:
                return f"base_case with {service}"
            return f"factorial({n}) -> {factorial(n-1)}"

        result = factorial(3)
        # Should work recursively
        assert "base_case with injected_service" in result
        assert "factorial(3)" in result


def test_partial_function_injection(test_scope):
    """Test @inject with functools.partial."""
    with test_scope:

        @inject
        def base_function(a: str, b: str, c: str, service: str = Inject["service"]) -> str:
            return f"a={a}, b={b}, c={c}, service={service}"

        # Create partial function
        partial_func = partial(base_function, "fixed_a", c="fixed_c")

        # Partial should work with injection
        result = partial_func("variable_b")
        assert result == "a=fixed_a, b=variable_b, c=fixed_c, service=injected_service"


# =============================================================================
# MEMORY AND GARBAGE COLLECTION
# =============================================================================


def test_weakref_compatibility(test_scope):
    """Test that @inject works with weakref."""
    with test_scope:

        @inject
        def injected_function(data: str, service: str = Inject["service"]) -> str:
            return f"{data}: {service}"

        # Should be able to create weak reference
        weak_ref = weakref.ref(injected_function)
        assert weak_ref() is not None

        # Function should still work
        result = injected_function("test")
        assert result == "test: injected_service"


def test_gc_interaction(test_scope):
    """Test interaction with garbage collection."""
    with test_scope:

        @inject
        def gc_test_function(data: str, service: str = Inject["service"]) -> str:
            return f"gc_test: {data} with {service}"

        # Force garbage collection
        gc.collect()

        # Function should still work after GC
        result = gc_test_function("after_gc")
        assert result == "gc_test: after_gc with injected_service"

        # Should work multiple times
        for i in range(10):
            result = gc_test_function(f"iteration_{i}")
            assert f"iteration_{i}" in result
            assert "injected_service" in result


# =============================================================================
# DESCRIPTORS AND METACLASSES
# =============================================================================


def test_descriptor_interaction(test_scope):
    """Test @inject with descriptor protocol."""
    with test_scope:

        class InjectedDescriptor:
            @inject
            def __get__(self, obj, objtype=None, service: str = Inject["service"]):
                if obj is None:
                    return self
                return f"descriptor value with {service}"

        class TestClass:
            attr = InjectedDescriptor()

        obj = TestClass()
        result = obj.attr
        assert result == "descriptor value with injected_service"


def test_metaclass_interaction(test_scope):
    """Test @inject with metaclasses."""
    with test_scope:

        class InjectedMeta(type):
            @inject
            def create_instance(cls, service: str = Inject["service"]):
                instance = cls()
                instance.service = service
                return instance

        class TestClass(metaclass=InjectedMeta):
            pass

        obj = TestClass.create_instance()
        assert obj.service == "injected_service"


# =============================================================================
# COMPLEX TYPE ANNOTATIONS AND SIGNATURES
# =============================================================================


def test_signature_complex_annotations(test_scope):
    """Test @inject with complex type annotations."""
    with test_scope:

        @inject
        def complex_annotations(
            data: list[str],
            mapping: dict[str, int],
            optional: str | None = None,
            union: str | int = "default",
            service: str = Inject["service"],
        ) -> str:
            return f"complex: {len(data)} items, {len(mapping)} keys, service={service}"

        result = complex_annotations(["a", "b"], {"x": 1, "y": 2})
        assert result == "complex: 2 items, 2 keys, service=injected_service"


def test_dynamic_parameter_creation(test_scope):
    """Test @inject with dynamically created functions."""
    with test_scope:
        # Create function dynamically
        def create_dynamic_function():
            def dynamic_func(name: str, service: str = Inject["service"]) -> str:
                return f"dynamic: {name} with {service}"

            return inject(dynamic_func)

        dynamic_func = create_dynamic_function()
        result = dynamic_func("test")
        assert result == "dynamic: test with injected_service"


def test_thread_local_injection(test_scope):
    """Test @inject with thread-local storage patterns (single-threaded simulation)."""
    import threading

    thread_data = threading.local()

    with test_scope:

        @inject
        def thread_worker(thread_id: int, service: str = Inject["service"]) -> str:
            thread_data.value = f"thread_{thread_id}"
            return f"{thread_data.value} using {service}"

        # Test thread-local data behavior within the same thread
        results = []
        for i in range(3):
            result = thread_worker(i)
            results.append(result)

        assert len(results) == 3
        # Each call should show the thread-local value changing
        assert results[0] == "thread_0 using injected_service"
        assert results[1] == "thread_1 using injected_service"
        assert results[2] == "thread_2 using injected_service"
