"""Tests for different parameter types: regular, keyword-only, positional-only."""

import sys

import pytest

from injectipy import DependencyNotFoundError, DependencyScope, Inject, PositionalOnlyInjectionError, inject


@pytest.fixture
def test_scope():
    """Provide a clean scope with test dependencies."""
    scope = DependencyScope()
    scope.register_value("service1", "injected_service1")
    scope.register_value("service2", "injected_service2")
    scope.register_value("config", {"debug": True})
    return scope


# =============================================================================
# KEYWORD-ONLY PARAMETER TESTS
# =============================================================================


def test_keyword_only_inject_basic(test_scope):
    """Test basic keyword-only parameter injection."""
    with test_scope:

        @inject
        def func(name: str, *, service: str = Inject["service1"]) -> str:
            return f"name={name}, service={service}"

        result = func("test")
        assert result == "name=test, service=injected_service1"


def test_keyword_only_inject_override(test_scope):
    """Test overriding keyword-only injected parameters."""
    with test_scope:

        @inject
        def func(name: str, *, service: str = Inject["service1"]) -> str:
            return f"name={name}, service={service}"

        result = func("test", service="custom_service")
        assert result == "name=test, service=custom_service"


def test_keyword_only_multiple_inject(test_scope):
    """Test multiple keyword-only injected parameters."""
    with test_scope:

        @inject
        def func(name: str, *, svc1: str = Inject["service1"], svc2: str = Inject["service2"]) -> str:
            return f"name={name}, svc1={svc1}, svc2={svc2}"

        result = func("test")
        assert result == "name=test, svc1=injected_service1, svc2=injected_service2"


def test_keyword_only_mixed_with_regular(test_scope):
    """Test mixing regular and keyword-only Inject parameters."""
    with test_scope:

        @inject
        def func(a: str, b: str = Inject["service1"], *, c: str = Inject["service2"], d: str = "default") -> str:
            return f"a={a}, b={b}, c={c}, d={d}"

        result = func("test")
        assert result == "a=test, b=injected_service1, c=injected_service2, d=default"

        # Override regular injection positionally
        result = func("test", "override1")
        assert result == "a=test, b=override1, c=injected_service2, d=default"

        # Override keyword-only injection
        result = func("test", c="override2")
        assert result == "a=test, b=injected_service1, c=override2, d=default"


def test_keyword_only_missing_dependency(test_scope):
    """Test keyword-only parameter with missing dependency."""
    with test_scope:

        @inject
        def func(name: str, *, missing: str = Inject["nonexistent"]) -> str:
            return f"{name}: {missing}"

        with pytest.raises(DependencyNotFoundError, match="Dependency 'nonexistent' not found"):
            func("test")


def test_keyword_only_only_inject(test_scope):
    """Test function with only keyword-only injected parameters."""
    with test_scope:

        @inject
        def func(*, service1: str = Inject["service1"], service2: str = Inject["service2"]) -> str:
            return f"service1={service1}, service2={service2}"

        result = func()
        assert result == "service1=injected_service1, service2=injected_service2"


def test_keyword_only_no_inject_defaults(test_scope):
    """Test keyword-only parameters without Inject defaults."""

    @inject
    def func(name: str, *, debug: bool = True, env: str = "test") -> str:
        return f"name={name}, debug={debug}, env={env}"

    result = func("test")
    assert result == "name=test, debug=True, env=test"


def test_keyword_only_exception_handling(test_scope):
    """Test exception handling with keyword-only parameters."""
    with test_scope:

        @inject
        def func(name: str, *, service: str = Inject["service1"]) -> str:
            if name == "error":
                raise ValueError("Intentional error")
            return f"{name}: {service}"

        # Normal case should work
        result = func("normal")
        assert result == "normal: injected_service1"

        # Exception should propagate correctly
        with pytest.raises(ValueError, match="Intentional error"):
            func("error")


def test_keyword_only_preserve_signature(test_scope):
    """Test that @inject preserves function signature for keyword-only params."""

    @inject
    def original_func(a: str, b: int = 10, *, c: str = Inject["service1"], d: bool = False) -> str:
        return f"a={a}, b={b}, c={c}, d={d}"

    import inspect

    sig = inspect.signature(original_func)

    # Check parameter kinds
    params = list(sig.parameters.values())
    assert params[0].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD  # a
    assert params[1].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD  # b
    assert params[2].kind == inspect.Parameter.KEYWORD_ONLY  # c
    assert params[3].kind == inspect.Parameter.KEYWORD_ONLY  # d


# =============================================================================
# POSITIONAL-ONLY PARAMETER TESTS
# =============================================================================


@pytest.mark.skipif(sys.version_info < (3, 8), reason="Positional-only parameters require Python 3.8+")
def test_positional_only_with_inject_raises_error(test_scope):
    """Test that positional-only parameters with Inject raise clear error."""
    with test_scope:
        # Use exec to avoid syntax errors on Python < 3.8
        code = """
with test_scope:
    @inject
    def func(pos_only, pos_inject=Inject["service1"], /, regular="default"):
        return f"pos_only={pos_only}, pos_inject={pos_inject}, regular={regular}"

    try:
        result = func("test")
        error_raised = False
    except PositionalOnlyInjectionError as e:
        error_raised = True
        error_message = str(e)
"""
        globals_dict = {
            "inject": inject,
            "Inject": Inject,
            "PositionalOnlyInjectionError": PositionalOnlyInjectionError,
            "test_scope": test_scope,
        }
        exec(code, globals_dict)

        # Should raise an error for positional-only injection
        assert globals_dict["error_raised"] is True
        assert "positional-only parameter" in globals_dict["error_message"]


@pytest.mark.skipif(sys.version_info < (3, 8), reason="Positional-only parameters require Python 3.8+")
def test_positional_only_without_inject_works(test_scope):
    """Test that positional-only parameters without Inject work fine."""
    with test_scope:
        code = """
with test_scope:
    @inject
    def func(pos_only, /, regular=Inject["service1"]):
        return f"pos_only={pos_only}, regular={regular}"

    result = func("test")
"""
        globals_dict = {
            "inject": inject,
            "Inject": Inject,
            "PositionalOnlyInjectionError": PositionalOnlyInjectionError,
            "test_scope": test_scope,
        }
        exec(code, globals_dict)

        assert globals_dict["result"] == "pos_only=test, regular=injected_service1"


# =============================================================================
# COMPLEX PARAMETER COMBINATIONS
# =============================================================================


def test_all_parameter_types_mixed(test_scope):
    """Test function with all parameter types mixed together."""
    with test_scope:

        @inject
        def complex_func(
            pos_required: str,
            pos_optional: str = "pos_default",
            pos_inject: str = Inject["service1"],
            *,
            kw_inject: str = Inject["service2"],
            kw_default: str = "kw_default",
        ) -> str:
            return f"pos_req={pos_required}, pos_opt={pos_optional}, pos_inj={pos_inject}, kw_inj={kw_inject}, kw_def={kw_default}"

        # All defaults
        result = complex_func("required")
        assert (
            result
            == "pos_req=required, pos_opt=pos_default, pos_inj=injected_service1, kw_inj=injected_service2, kw_def=kw_default"
        )

        # Override positional
        result = complex_func("required", "custom_pos")
        assert (
            result
            == "pos_req=required, pos_opt=custom_pos, pos_inj=injected_service1, kw_inj=injected_service2, kw_def=kw_default"
        )

        # Override keyword-only
        result = complex_func("required", kw_inject="custom_kw")
        assert (
            result
            == "pos_req=required, pos_opt=pos_default, pos_inj=injected_service1, kw_inj=custom_kw, kw_def=kw_default"
        )


def test_optional_dependencies_with_defaults(test_scope):
    """Test parameters with both regular defaults and Inject defaults."""
    with test_scope:

        @inject
        def func_with_optional_deps(
            name: str, service: str = Inject["service1"], fallback: str = "default_fallback"
        ) -> str:
            return f"name={name}, service={service}, fallback={fallback}"

        result = func_with_optional_deps("test")
        assert result == "name=test, service=injected_service1, fallback=default_fallback"

        # Override injected parameter
        result = func_with_optional_deps("test", service="custom")
        assert result == "name=test, service=custom, fallback=default_fallback"

        # Override regular default
        result = func_with_optional_deps("test", fallback="custom_fallback")
        assert result == "name=test, service=injected_service1, fallback=custom_fallback"


def test_parameter_order_preservation(test_scope):
    """Test that parameter order is preserved correctly."""
    with test_scope:

        @inject
        def ordered_func(
            a: str,
            b: str = "b_default",
            c: str = Inject["service1"],
            d: str = "d_default",
            *,
            e: str = Inject["service2"],
            f: str = "f_default",
        ) -> str:
            return f"a={a}, b={b}, c={c}, d={d}, e={e}, f={f}"

        result = ordered_func("a_value")
        expected = "a=a_value, b=b_default, c=injected_service1, d=d_default, e=injected_service2, f=f_default"
        assert result == expected
