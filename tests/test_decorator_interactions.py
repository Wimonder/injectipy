"""Tests for @inject decorator interactions with other decorators."""

import sys

import pytest

from injectipy import Inject, InjectipyStore, inject


@pytest.fixture
def store() -> InjectipyStore:
    store_instance = InjectipyStore()
    store_instance._reset_for_testing()
    return store_instance


class TestClassmethodInteractions:
    """Test @inject decorator with @classmethod."""

    def test_inject_then_classmethod(self, store: InjectipyStore):
        """Test @inject -> @classmethod decorator order."""
        store.register_value("service", "injected_service")

        class TestClass:
            @inject
            @classmethod
            def method(cls, a=Inject["service"]):
                return f"cls={cls.__name__}, a={a}"

        result = TestClass.method()
        assert result == "cls=TestClass, a=injected_service"

    def test_classmethod_then_inject(self, store: InjectipyStore):
        """Test @classmethod -> @inject decorator order."""
        store.register_value("service", "injected_service")

        class TestClass:
            @classmethod
            @inject
            def method(cls, a=Inject["service"]):
                return f"cls={cls.__name__}, a={a}"

        result = TestClass.method()
        assert result == "cls=TestClass, a=injected_service"

    def test_classmethod_with_multiple_parameters(self, store: InjectipyStore):
        """Test classmethod with multiple injected parameters."""
        store.register_value("service1", "injected_service1")
        store.register_value("service2", "injected_service2")

        class TestClass:
            @inject
            @classmethod
            def method(cls, pos_arg, a=Inject["service1"], b=Inject["service2"], c="default"):
                return f"cls={cls.__name__}, pos={pos_arg}, a={a}, b={b}, c={c}"

        result = TestClass.method("test")
        assert result == "cls=TestClass, pos=test, a=injected_service1, b=injected_service2, c=default"

        # Test with overrides
        result = TestClass.method("test", "override1", c="custom")
        assert result == "cls=TestClass, pos=test, a=override1, b=injected_service2, c=custom"

    def test_classmethod_with_keyword_only_params(self, store: InjectipyStore):
        """Test classmethod with keyword-only injected parameters."""
        store.register_value("service", "injected_service")

        class TestClass:
            @inject
            @classmethod
            def method(cls, pos_arg, *, kw_inject=Inject["service"], kw_default="default"):
                return f"cls={cls.__name__}, pos={pos_arg}, kw_inject={kw_inject}, kw_default={kw_default}"

        result = TestClass.method("test")
        assert result == "cls=TestClass, pos=test, kw_inject=injected_service, kw_default=default"

        # Test with override
        result = TestClass.method("test", kw_inject="override")
        assert result == "cls=TestClass, pos=test, kw_inject=override, kw_default=default"

    def test_classmethod_missing_dependency(self, store: InjectipyStore):
        """Test classmethod with missing dependency."""

        class TestClass:
            @inject
            @classmethod
            def method(cls, a=Inject["missing_service"]):
                return f"cls={cls.__name__}, a={a}"

        with pytest.raises(RuntimeError, match="Could not resolve missing_service"):
            TestClass.method()


class TestStaticmethodInteractions:
    """Test @inject decorator with @staticmethod."""

    def test_inject_then_staticmethod(self, store: InjectipyStore):
        """Test @inject -> @staticmethod decorator order."""
        store.register_value("service", "injected_service")

        class TestClass:
            @inject
            @staticmethod
            def method(a=Inject["service"]):
                return f"a={a}"

        result = TestClass.method()
        assert result == "a=injected_service"

    def test_staticmethod_then_inject(self, store: InjectipyStore):
        """Test @staticmethod -> @inject decorator order."""
        store.register_value("service", "injected_service")

        class TestClass:
            @staticmethod
            @inject
            def method(a=Inject["service"]):
                return f"a={a}"

        result = TestClass.method()
        assert result == "a=injected_service"

    def test_staticmethod_with_multiple_parameters(self, store: InjectipyStore):
        """Test staticmethod with multiple injected parameters."""
        store.register_value("service1", "injected_service1")
        store.register_value("service2", "injected_service2")

        class TestClass:
            @inject
            @staticmethod
            def method(pos_arg, a=Inject["service1"], b=Inject["service2"], c="default"):
                return f"pos={pos_arg}, a={a}, b={b}, c={c}"

        result = TestClass.method("test")
        assert result == "pos=test, a=injected_service1, b=injected_service2, c=default"

        # Test with overrides
        result = TestClass.method("test", "override1", c="custom")
        assert result == "pos=test, a=override1, b=injected_service2, c=custom"

    def test_staticmethod_with_keyword_only_params(self, store: InjectipyStore):
        """Test staticmethod with keyword-only injected parameters."""
        store.register_value("service", "injected_service")

        class TestClass:
            @inject
            @staticmethod
            def method(pos_arg, *, kw_inject=Inject["service"], kw_default="default"):
                return f"pos={pos_arg}, kw_inject={kw_inject}, kw_default={kw_default}"

        result = TestClass.method("test")
        assert result == "pos=test, kw_inject=injected_service, kw_default=default"

        # Test with override
        result = TestClass.method("test", kw_inject="override")
        assert result == "pos=test, kw_inject=override, kw_default=default"

    def test_staticmethod_missing_dependency(self, store: InjectipyStore):
        """Test staticmethod with missing dependency."""

        class TestClass:
            @inject
            @staticmethod
            def method(a=Inject["missing_service"]):
                return f"a={a}"

        with pytest.raises(RuntimeError, match="Could not resolve missing_service"):
            TestClass.method()


class TestComplexDecoratorInteractions:
    """Test complex decorator interaction scenarios."""

    def test_multiple_decorators_with_inject(self, store: InjectipyStore):
        """Test @inject with multiple other decorators.

        Note: @inject should come after @classmethod/@staticmethod but before
        other function decorators for best compatibility.
        """
        store.register_value("service", "injected_service")

        def custom_decorator(func):
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                return f"custom({result})"

            return wrapper

        # Test regular function with multiple decorators
        @custom_decorator
        @inject
        def regular_function(a=Inject["service"]):
            return f"a={a}"

        result = regular_function()
        assert result == "custom(a=injected_service)"

        # Test recommended order for class methods
        class TestClass:
            @inject
            @classmethod
            def method(cls, a=Inject["service"]):
                return f"cls={cls.__name__}, a={a}"

        result = TestClass.method()
        assert result == "cls=TestClass, a=injected_service"

    def test_property_with_inject(self, store: InjectipyStore):
        """Test @property with @inject (edge case)."""
        store.register_value("service", "injected_service")

        class TestClass:
            @property
            @inject
            def prop(self, a=Inject["service"]):
                return f"a={a}"

        # Properties don't work with injection since they don't accept parameters
        # but let's test that it doesn't crash
        obj = TestClass()
        result = obj.prop  # This should work due to our implementation
        assert "a=injected_service" in result

    @pytest.mark.skipif(sys.version_info < (3, 8), reason="Positional-only parameters require Python 3.8+")
    def test_positional_only_with_classmethod(self, store: InjectipyStore):
        """Test positional-only parameters with classmethod."""
        store.register_value("service", "injected_service")

        # Use exec to avoid syntax errors on Python < 3.8
        code = """
class TestClass:
    @inject
    @classmethod
    def method(cls, pos_only, pos_inject=Inject["service"], /, regular="default"):
        return f"cls={cls.__name__}, pos_only={pos_only}, pos_inject={pos_inject}, regular={regular}"

result = TestClass.method("test_pos")
"""
        globals_dict = {"inject": inject, "Inject": Inject}
        exec(code, globals_dict)
        result = globals_dict["result"]
        assert result == "cls=TestClass, pos_only=test_pos, pos_inject=injected_service, regular=default"

    def test_inheritance_with_decorated_methods(self, store: InjectipyStore):
        """Test inheritance with injected class methods."""
        store.register_value("base_service", "base_injected")
        store.register_value("derived_service", "derived_injected")

        class BaseClass:
            @inject
            @classmethod
            def base_method(cls, a=Inject["base_service"]):
                return f"base_cls={cls.__name__}, a={a}"

        class DerivedClass(BaseClass):
            @inject
            @classmethod
            def derived_method(cls, b=Inject["derived_service"]):
                return f"derived_cls={cls.__name__}, b={b}"

        # Test base method from base class
        result = BaseClass.base_method()
        assert result == "base_cls=BaseClass, a=base_injected"

        # Test base method from derived class
        result = DerivedClass.base_method()
        assert result == "base_cls=DerivedClass, a=base_injected"

        # Test derived method
        result = DerivedClass.derived_method()
        assert result == "derived_cls=DerivedClass, b=derived_injected"

    def test_decorator_preservation_of_metadata(self, store: InjectipyStore):
        """Test that decorator preserves function metadata."""
        store.register_value("service", "injected_service")

        class TestClass:
            @inject
            @classmethod
            def documented_method(cls, a=Inject["service"]):
                """This method has documentation."""
                return f"cls={cls.__name__}, a={a}"

        # Test that metadata is preserved
        assert TestClass.documented_method.__doc__ == "This method has documentation."
        assert TestClass.documented_method.__name__ == "documented_method"
