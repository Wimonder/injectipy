import asyncio
import functools
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar, cast, overload

from injectipy.exceptions import AsyncDependencyError, DependencyNotFoundError, PositionalOnlyInjectionError
from injectipy.models.inject import Inject

F = TypeVar("F", bound=Callable[..., Any])
AsyncF = TypeVar("AsyncF", bound=Callable[..., Awaitable[Any]])

if TYPE_CHECKING:
    from injectipy.scope import DependencyScope


@dataclass(frozen=True)
class _InjectionPoint:
    """A parameter to inject, resolved once at decoration time."""

    name: str
    key: Any
    position: int | None  # Index among positional parameters, None for keyword-only
    positional_only: bool


def _collect_injection_points(func: Callable[..., Any]) -> list[_InjectionPoint]:
    """Find the parameters marked with Inject[key].

    Objects without an introspectable signature, such as property, get no
    injection points and are left untouched.
    """
    try:
        parameters = list(inspect.signature(func).parameters.values())
    except (TypeError, ValueError):
        return []
    positional_kinds = (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    positional_parameters = [param for param in parameters if param.kind in positional_kinds]

    points = [
        _InjectionPoint(
            name=param.name,
            key=param.default.get_inject_key(),
            position=position,
            positional_only=param.kind is inspect.Parameter.POSITIONAL_ONLY,
        )
        for position, param in enumerate(positional_parameters)
        if isinstance(param.default, Inject)
    ]
    points += [
        _InjectionPoint(name=param.name, key=param.default.get_inject_key(), position=None, positional_only=False)
        for param in parameters
        if param.kind is inspect.Parameter.KEYWORD_ONLY and isinstance(param.default, Inject)
    ]
    return points


def _is_supplied(point: _InjectionPoint, args: tuple[Any, ...], kwargs: dict[str, Any]) -> bool:
    """Check if the caller passed this parameter explicitly."""
    if point.position is not None and point.position < len(args):
        return True
    return point.name in kwargs


def _check_for_async_dependency(
    inject_key: Any,
    param_name: str,
    function_name: str,
    module_name: str | None = None,
    explicit_scopes: list["DependencyScope"] | None = None,
) -> None:
    """Check if dependency key corresponds to an async resolver and raise error if used with @inject."""
    from injectipy.scope import get_active_scopes

    # Check explicit scopes first
    if explicit_scopes:
        for scope in reversed(explicit_scopes):
            if scope.contains(inject_key):
                if scope._is_async_resolver(inject_key):
                    raise AsyncDependencyError(
                        function_name=function_name,
                        parameter_name=param_name,
                        dependency_key=inject_key,
                        module_name=module_name,
                    )
                return  # Found in explicit scope, no need to check active scopes

    # Check active scopes for async resolvers
    active_scopes = get_active_scopes()
    for scope in reversed(active_scopes):  # Check innermost first
        if scope.contains(inject_key):
            if scope._is_async_resolver(inject_key):
                raise AsyncDependencyError(
                    function_name=function_name,
                    parameter_name=param_name,
                    dependency_key=inject_key,
                    module_name=module_name,
                )
            break  # Found in this scope, no need to check others


def _resolve_with_async_check(
    inject_key: Any,
    param_name: str,
    function_name: str,
    module_name: str | None,
    explicit_scopes: list["DependencyScope"] | None,
) -> Any:
    """Helper to resolve dependency with async check to reduce code duplication."""
    # Check if this is an async dependency - not allowed with @inject
    _check_for_async_dependency(
        inject_key=inject_key,
        param_name=param_name,
        function_name=function_name,
        module_name=module_name,
        explicit_scopes=explicit_scopes,
    )

    from injectipy.scope import resolve_dependency

    return resolve_dependency(inject_key, explicit_scopes)


@overload
def inject(fn: F) -> F: ...


@overload
def inject(*, scopes: list["DependencyScope"] | None = ...) -> Callable[[F], F]: ...


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
    original_func = fn.__func__ if (is_classmethod or is_staticmethod) else fn  # type: ignore[attr-defined]

    # Signature inspection happens once here, not on every call.
    points = _collect_injection_points(original_func)
    module_name = getattr(original_func, "__module__", None)

    if not points:
        return fn

    @functools.wraps(original_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        for point in points:
            if _is_supplied(point, args, kwargs):
                continue

            if point.positional_only:
                raise PositionalOnlyInjectionError(
                    function_name=original_func.__name__,
                    parameter_name=point.name,
                    dependency_key=point.key,
                    module_name=module_name,
                )

            try:
                kwargs[point.name] = _resolve_with_async_check(
                    inject_key=point.key,
                    param_name=point.name,
                    function_name=original_func.__name__,
                    module_name=module_name,
                    explicit_scopes=explicit_scopes,
                )
            except DependencyNotFoundError as e:
                raise DependencyNotFoundError(
                    key=point.key,
                    function_name=original_func.__name__,
                    module_name=module_name,
                    parameter_name=point.name,
                    available_keys=e.available_keys,
                ) from e

        return original_func(*args, **kwargs)

    if is_classmethod:
        return cast(F, classmethod(wrapper))
    elif is_staticmethod:
        return cast(F, staticmethod(wrapper))
    else:
        return cast(F, wrapper)


@overload
def ainject(fn: AsyncF) -> AsyncF: ...


@overload
def ainject(*, scopes: list["DependencyScope"] | None = ...) -> Callable[[AsyncF], AsyncF]: ...


def ainject(
    fn: AsyncF | None = None, *, scopes: list["DependencyScope"] | None = None
) -> AsyncF | Callable[[AsyncF], AsyncF]:
    """Async decorator to enable automatic dependency injection for async function parameters.

    This decorator scans async function parameters for Inject[key] annotations and
    automatically resolves those dependencies from active dependency scopes, properly
    awaiting any async dependencies before calling the target function.

    Dependencies are resolved in this order:
    1. Explicit scopes (if provided to the decorator)
    2. Active scope stack (innermost scope wins)

    The decorator preserves the original function signature and only affects
    parameters that have Inject[key] default values. Regular parameters and
    arguments passed explicitly are handled normally.

    Unlike the sync @inject decorator, @ainject properly handles async dependencies
    by awaiting them before calling the target function, eliminating the need for
    manual hasattr(..., '__await__') checks.

    Args:
        fn: The async function to decorate
        scopes: Optional list of explicit scopes to use for dependency resolution

    Returns:
        The decorated async function with dependency injection enabled

    Raises:
        DependencyNotFoundError: If a required dependency cannot be resolved
        PositionalOnlyInjectionError: If trying to inject into positional-only parameter

    Examples:
        Basic usage with active scopes:
        >>> from injectipy import ainject, Inject, DependencyScope
        >>>
        >>> async with DependencyScope() as scope:
        ...     scope.register_async_resolver("api", create_api_client)
        ...
        ...     @ainject
        ...     async def fetch_data(endpoint: str, api: ApiClient = Inject["api"]):
        ...         # api is already resolved, no await needed
        ...         return await api.get(endpoint)
        ...
        ...     result = await fetch_data("/users")  # api automatically injected and awaited

        With explicit scopes:
        >>> scope = DependencyScope()
        >>> scope.register_async_resolver("service", create_service)
        >>>
        >>> @ainject(scopes=[scope])
        >>> async def process_data(service: Service = Inject["service"]):
        ...     # service is pre-resolved
        ...     return await service.process()

    Note:
        - Only works with async functions
        - Async dependencies are automatically awaited before function execution
        - Sync dependencies work normally
        - Mixed sync/async dependencies are supported
        - Explicitly passed arguments always override injection
    """

    def decorator(func: AsyncF) -> AsyncF:
        return _create_async_injected_function(func, scopes)

    if fn is None:
        # Called with arguments: @ainject(scopes=[...])
        return decorator
    else:
        # Called without arguments: @ainject
        return decorator(fn)


async def resolve_dependency_async(key: Any, additional_scopes: list["DependencyScope"] | None = None) -> Any:
    """Async version of resolve_dependency that properly awaits async dependencies.

    Args:
        key: The dependency key to resolve
        additional_scopes: Optional list of additional scopes to search

    Returns:
        The resolved dependency value (with async dependencies properly awaited)

    Raises:
        DependencyNotFoundError: If dependency not found in any scope
    """
    from injectipy.scope import resolve_dependency

    # First resolve the dependency (may be sync value, Task, or other awaitable)
    resolved_value = resolve_dependency(key, additional_scopes)

    # If it's awaitable, await it
    if hasattr(resolved_value, "__await__"):
        return await resolved_value

    return resolved_value


def _create_async_injected_function(fn: AsyncF, explicit_scopes: list["DependencyScope"] | None = None) -> AsyncF:
    """Create the actual async injected function implementation."""
    is_classmethod = isinstance(fn, classmethod)
    is_staticmethod = isinstance(fn, staticmethod)
    original_func = fn.__func__ if (is_classmethod or is_staticmethod) else fn  # type: ignore[attr-defined]

    # Validate that the function is actually async
    if not asyncio.iscoroutinefunction(original_func):
        raise TypeError(f"@ainject can only be used with async functions, got {original_func.__name__}")

    # Signature inspection happens once here, not on every call.
    points = _collect_injection_points(original_func)
    module_name = getattr(original_func, "__module__", None)

    if not points:
        return fn

    @functools.wraps(original_func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        for point in points:
            if _is_supplied(point, args, kwargs):
                continue

            if point.positional_only:
                raise PositionalOnlyInjectionError(
                    function_name=original_func.__name__,
                    parameter_name=point.name,
                    dependency_key=point.key,
                    module_name=module_name,
                )

            try:
                kwargs[point.name] = await resolve_dependency_async(point.key, explicit_scopes)
            except DependencyNotFoundError as e:
                raise DependencyNotFoundError(
                    key=point.key,
                    function_name=original_func.__name__,
                    module_name=module_name,
                    parameter_name=point.name,
                    available_keys=e.available_keys,
                ) from e

        # Call the original async function with resolved dependencies
        return await original_func(*args, **kwargs)

    if is_classmethod:
        return cast(AsyncF, classmethod(async_wrapper))
    elif is_staticmethod:
        return cast(AsyncF, staticmethod(async_wrapper))
    else:
        return cast(AsyncF, async_wrapper)


__all__ = ["inject", "ainject"]
