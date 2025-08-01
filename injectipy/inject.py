import functools
import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar, cast

from injectipy.exceptions import DependencyNotFoundError, PositionalOnlyInjectionError
from injectipy.models.inject import Inject

F = TypeVar("F", bound=Callable[..., Any])

if TYPE_CHECKING:
    from injectipy.scope import DependencyScope


def inject(fn: F | None = None, *, scopes: list["DependencyScope"] | None = None) -> F | Callable[[F], F]:
    """Decorator to enable automatic dependency injection for function parameters.

    This decorator scans function parameters for Inject[key] annotations and
    automatically resolves those dependencies from active dependency scopes.

    Dependencies are resolved in this order:
    1. Explicit scopes (if provided to the decorator)
    2. Active scope stack (innermost scope wins)

    The decorator preserves the original function signature and only affects
    parameters that have Inject[key] default values. Regular parameters and
    arguments passed explicitly are handled normally.

    Works with regular parameters, keyword-only parameters, classmethod and staticmethod.

    Args:
        fn: The function, classmethod, or staticmethod to decorate
        scopes: Optional list of explicit scopes to use for dependency resolution

    Returns:
        The decorated function with dependency injection enabled

    Raises:
        DependencyNotFoundError: If a required dependency cannot be resolved
        PositionalOnlyInjectionError: If trying to inject into positional-only parameter

    Examples:
        Basic usage with active scopes:
        >>> from injectipy import inject, Inject, DependencyScope
        >>>
        >>> with DependencyScope() as scope:
        ...     scope.register_value("config", {"debug": True})
        ...
        ...     @inject
        ...     def my_function(name: str, config: dict = Inject["config"]):
        ...         return f"Hello {name}, debug={config['debug']}"
        ...
        ...     result = my_function("Alice")  # config automatically injected

        With explicit scopes:
        >>> scope = DependencyScope()
        >>> scope.register_value("service", "TestService")
        >>>
        >>> @inject(scopes=[scope])
        >>> def explicit_scoped_function(service: str = Inject["service"]):
        ...     return service

    Note:
        - Only parameters with Inject[key] defaults are injected
        - Explicitly passed arguments always override injection
        - Works with regular and keyword-only parameters
        - For classmethod/staticmethod: use @classmethod/@staticmethod first, then @inject
        - Explicit scopes have highest priority, followed by active scopes
    """

    def decorator(func: F) -> F:
        return _create_injected_function(func, scopes)

    if fn is None:
        # Called with arguments: @inject(scopes=[...])
        return decorator
    else:
        # Called without arguments: @inject
        return decorator(fn)


def _create_injected_function(fn: F, explicit_scopes: list["DependencyScope"] | None = None) -> F:
    """Create the actual injected function implementation."""
    is_classmethod = isinstance(fn, classmethod)
    is_staticmethod = isinstance(fn, staticmethod)

    if is_classmethod or is_staticmethod:
        original_func = fn.__func__  # type: ignore[attr-defined]
        original_defaults = original_func.__defaults__
        original_kwdefaults = original_func.__kwdefaults__
    else:
        original_func = fn
        original_defaults = getattr(fn, "__defaults__", None)
        original_kwdefaults = getattr(fn, "__kwdefaults__", None)

    has_inject_defaults = False

    if original_defaults:
        has_inject_defaults = any(isinstance(default, Inject) for default in original_defaults)

    if original_kwdefaults:
        has_inject_defaults = has_inject_defaults or any(
            isinstance(default, Inject) for default in original_kwdefaults.values()
        )

    if not has_inject_defaults:
        return fn

    @functools.wraps(original_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        resolved_kwargs = kwargs.copy()
        sig = inspect.signature(original_func)
        bound_args = sig.bind_partial(*args, **kwargs)

        if original_defaults:
            param_list = list(sig.parameters.values())
            regular_params = [
                p
                for p in param_list
                if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            ]
            params_with_defaults = regular_params[-len(original_defaults) :]

            for param, default in zip(params_with_defaults, original_defaults, strict=False):
                if isinstance(default, Inject):
                    if param.name not in bound_args.arguments:
                        inject_key = default.get_inject_key()
                        try:
                            from injectipy.scope import resolve_dependency

                            resolved_value = resolve_dependency(inject_key, explicit_scopes)

                            if param.kind == inspect.Parameter.POSITIONAL_ONLY:
                                raise PositionalOnlyInjectionError(
                                    function_name=original_func.__name__,
                                    parameter_name=param.name,
                                    dependency_key=inject_key,
                                    module_name=getattr(original_func, "__module__", None),
                                )
                            else:
                                resolved_kwargs[param.name] = resolved_value
                        except DependencyNotFoundError as e:
                            raise DependencyNotFoundError(
                                key=inject_key,
                                function_name=original_func.__name__,
                                module_name=getattr(original_func, "__module__", None),
                                parameter_name=param.name,
                                available_keys=e.available_keys,
                            ) from e

        if original_kwdefaults:
            for param_name, default in original_kwdefaults.items():
                if isinstance(default, Inject):
                    if param_name not in resolved_kwargs:
                        inject_key = default.get_inject_key()
                        try:
                            from injectipy.scope import resolve_dependency

                            resolved_kwargs[param_name] = resolve_dependency(inject_key, explicit_scopes)
                        except DependencyNotFoundError as e:
                            raise DependencyNotFoundError(
                                key=inject_key,
                                function_name=original_func.__name__,
                                module_name=getattr(original_func, "__module__", None),
                                parameter_name=param_name,
                                available_keys=e.available_keys,
                            ) from e

        return original_func(*args, **resolved_kwargs)

    if is_classmethod:
        return cast(F, classmethod(wrapper))
    elif is_staticmethod:
        return cast(F, staticmethod(wrapper))
    else:
        return cast(F, wrapper)


__all__ = ["inject"]
