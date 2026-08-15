"""Dependency scope management with context managers for explicit scoping."""

import asyncio
import contextvars
import inspect
import threading
from collections.abc import Callable, Coroutine, Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, TypeAlias, TypeVar, overload

from injectipy.exceptions import (
    CircularDependencyError,
    DependencyNotFoundError,
    DuplicateRegistrationError,
    InvalidStoreOperationError,
)
from injectipy.models.inject import Inject

T = TypeVar("T")

StoreKeyType: TypeAlias = str | type
StoreResolverType: TypeAlias = Callable[..., Any]

# Context variable for scope stack - works for both threads and async tasks
_scope_stack: contextvars.ContextVar[tuple["DependencyScope", ...]] = contextvars.ContextVar(
    "injectipy_scope_stack", default=()
)


@dataclass(frozen=True)
class _StoreResolverWithArgs:
    resolver: StoreResolverType
    evaluate_once: bool


@dataclass(frozen=True)
class _AsyncStoreResolverWithArgs:
    async_resolver: Callable[..., Coroutine[Any, Any, Any]]
    evaluate_once: bool
    sync_wrapper: StoreResolverType  # The sync wrapper function


_StoreValueType = _StoreResolverWithArgs | _AsyncStoreResolverWithArgs | Any


def _get_scope_stack() -> list["DependencyScope"]:
    """Get the current scope stack from context variables.

    This works correctly for both threading and asyncio contexts.
    """
    return list(_scope_stack.get())


def _set_scope_stack(stack: list["DependencyScope"]) -> None:
    """Set the scope stack in the current context."""
    _scope_stack.set(tuple(stack))


def _get_parameters(func: Callable[..., Any]) -> Mapping[str, inspect.Parameter]:
    """Get the parameters of a callable.

    Builtins without an introspectable signature are treated as taking no parameters.
    """
    try:
        return inspect.signature(func).parameters
    except (TypeError, ValueError):
        return {}


class DependencyScope:
    """A dependency scope that can be used as a context manager.

    This is the core dependency injection container that replaces the global store.
    Scopes can be nested, and dependencies are resolved from the most specific
    (innermost) scope first.

    Features:
    - Thread-safe dependency registration and resolution
    - Circular dependency detection
    - Type safety with mypy support
    - Lazy evaluation with optional caching
    - Forward reference support
    - Context manager for automatic cleanup

    Example:
        >>> with DependencyScope() as scope:
        ...     scope.register_value("config", {"debug": True})
        ...
        ...     @inject
        ...     def my_function(config: dict = Inject["config"]):
        ...         return config
        ...
        ...     result = my_function()  # Uses scoped config
    """

    def __init__(self) -> None:
        """Initialize a new dependency scope."""
        self._registry: dict[StoreKeyType, _StoreValueType] = {}
        self._cache: dict[StoreKeyType, Any] = {}
        self._async_resolver_cache: dict[StoreKeyType, bool] = {}  # Cache for async resolver lookups
        self._registry_lock = threading.RLock()
        self._resolution_locks: dict[StoreKeyType, Any] = {}  # Per-key locks for evaluate_once resolvers

    def register_value(self, key: StoreKeyType, value: Any, *, replace: bool = False) -> "DependencyScope":
        """Register a static value in this scope.

        Args:
            key: The dependency key
            value: The value to register
            replace: If True, replace an existing registration for this key

        Returns:
            Self for method chaining

        Raises:
            DuplicateRegistrationError: If key already exists and replace is False
        """
        with self._registry_lock:
            self._prepare_registration(key, replace)
            self._registry[key] = value
            self._cache[key] = value
            self._async_resolver_cache[key] = False  # Values are not async resolvers
        return self

    def register_resolver(
        self, key: StoreKeyType, resolver: StoreResolverType, *, evaluate_once: bool = False, replace: bool = False
    ) -> "DependencyScope":
        """Register a factory function in this scope.

        Args:
            key: The dependency key
            resolver: Factory function that creates the dependency
            evaluate_once: If True, cache the result after first evaluation
            replace: If True, replace an existing registration for this key

        Returns:
            Self for method chaining

        Raises:
            DuplicateRegistrationError: If key already exists and replace is False
            CircularDependencyError: If circular dependency detected
        """
        with self._registry_lock:
            self._prepare_registration(key, replace)
            self._check_circular_dependencies(key, resolver)
            self._registry[key] = _StoreResolverWithArgs(resolver, evaluate_once)
            self._async_resolver_cache[key] = False  # Sync resolvers are not async
        return self

    def register_async_resolver(
        self,
        key: StoreKeyType,
        async_resolver: Callable[..., Coroutine[Any, Any, Any]],
        *,
        evaluate_once: bool = False,
        replace: bool = False,
    ) -> "DependencyScope":
        """Register an async factory function.

        Args:
            key: The dependency key
            async_resolver: Async factory function that creates the dependency
            evaluate_once: If True, cache the result after first evaluation
            replace: If True, replace an existing registration for this key

        Returns:
            Self for method chaining

        Raises:
            DuplicateRegistrationError: If key already exists and replace is False
            CircularDependencyError: If circular dependency detected
        """

        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Check if we're in an async context
            try:
                loop = asyncio.get_running_loop()
                # If we're already in an async context, run the coroutine directly
                # Note: This creates a coroutine that needs to be awaited
                coro = async_resolver(*args, **kwargs)
                # Create a task to run it
                task = loop.create_task(coro)
                return task
            except RuntimeError:
                # If not in async context, run it synchronously
                return asyncio.run(async_resolver(*args, **kwargs))

        with self._registry_lock:
            self._prepare_registration(key, replace)
            self._check_circular_dependencies(key, async_resolver)
            # Store as an async resolver with a special marker
            self._registry[key] = _AsyncStoreResolverWithArgs(async_resolver, evaluate_once, sync_wrapper)
            self._async_resolver_cache[key] = True  # Cache that this is an async resolver
        return self

    def unregister(self, key: StoreKeyType) -> "DependencyScope":
        """Remove a dependency and anything cached for it.

        Args:
            key: The dependency key

        Returns:
            Self for method chaining

        Raises:
            DependencyNotFoundError: If key is not registered in this scope
        """
        with self._registry_lock:
            if key not in self._registry:
                raise DependencyNotFoundError(key=key, available_keys=list(self._registry.keys()))
            self._discard(key)
        return self

    def clear(self) -> "DependencyScope":
        """Remove all dependencies registered in this scope.

        Returns:
            Self for method chaining
        """
        with self._registry_lock:
            self._registry.clear()
            self._cache.clear()
            self._async_resolver_cache.clear()
            self._resolution_locks.clear()
        return self

    def _prepare_registration(self, key: StoreKeyType, replace: bool) -> None:
        if key not in self._registry:
            return
        if not replace:
            raise DuplicateRegistrationError(key, existing_type=self._registration_type(key))
        self._discard(key)

    def _registration_type(self, key: StoreKeyType) -> str:
        existing_entry = self._registry[key]
        if isinstance(existing_entry, _StoreResolverWithArgs):
            return "resolver"
        if isinstance(existing_entry, _AsyncStoreResolverWithArgs):
            return "async_resolver"
        return "value"

    def _discard(self, key: StoreKeyType) -> None:
        self._registry.pop(key, None)
        self._cache.pop(key, None)
        self._async_resolver_cache.pop(key, None)
        self._resolution_locks.pop(key, None)

    def _check_circular_dependencies(
        self, new_key: StoreKeyType, new_resolver: StoreResolverType | Callable[..., Coroutine[Any, Any, Any]]
    ) -> None:
        new_dependencies = self._get_resolver_dependencies(new_resolver)

        for dep_key in new_dependencies:
            if self._has_dependency_path(dep_key, new_key, set()):
                dependency_chain = self._build_dependency_chain(dep_key, new_key, [])
                raise CircularDependencyError(
                    dependency_chain=dependency_chain, new_key=new_key, conflicting_key=dep_key
                )

    def _get_resolver_dependencies(
        self, resolver: StoreResolverType | Callable[..., Coroutine[Any, Any, Any]]
    ) -> set[StoreKeyType]:
        dependencies = set()

        for param in _get_parameters(resolver).values():
            if param.default is not inspect.Parameter.empty and isinstance(param.default, Inject):
                dependencies.add(param.default.get_inject_key())

        return dependencies

    def _has_dependency_path(self, from_key: StoreKeyType, to_key: StoreKeyType, visited: set[StoreKeyType]) -> bool:
        if from_key == to_key:
            return True

        if from_key in visited:
            return False

        if from_key not in self._registry:
            return False

        visited.add(from_key)
        registry_entry = self._registry[from_key]
        if isinstance(registry_entry, _StoreResolverWithArgs):
            dependencies = self._get_resolver_dependencies(registry_entry.resolver)
            for dep_key in dependencies:
                if self._has_dependency_path(dep_key, to_key, visited.copy()):
                    return True
        elif isinstance(registry_entry, _AsyncStoreResolverWithArgs):
            dependencies = self._get_resolver_dependencies(registry_entry.async_resolver)
            for dep_key in dependencies:
                if self._has_dependency_path(dep_key, to_key, visited.copy()):
                    return True

        return False

    def _build_dependency_chain(
        self, from_key: StoreKeyType, to_key: StoreKeyType, current_chain: list[StoreKeyType]
    ) -> list[StoreKeyType]:
        if from_key == to_key:
            return current_chain + [from_key]

        if from_key not in self._registry:
            return current_chain + [from_key]

        registry_entry = self._registry[from_key]
        if isinstance(registry_entry, _StoreResolverWithArgs):
            dependencies = self._get_resolver_dependencies(registry_entry.resolver)
            for dep_key in dependencies:
                if dep_key not in current_chain:
                    chain = self._build_dependency_chain(dep_key, to_key, current_chain + [from_key])
                    if chain and chain[-1] == to_key:
                        return chain
        elif isinstance(registry_entry, _AsyncStoreResolverWithArgs):
            dependencies = self._get_resolver_dependencies(registry_entry.async_resolver)
            for dep_key in dependencies:
                if dep_key not in current_chain:
                    chain = self._build_dependency_chain(dep_key, to_key, current_chain + [from_key])
                    if chain and chain[-1] == to_key:
                        return chain

        return current_chain + [from_key]

    @overload
    def __getitem__(self, key: str) -> Any: ...

    @overload
    def __getitem__(self, key: type[T]) -> T: ...

    def __getitem__(self, key: Any) -> Any:
        """Get a dependency from this scope only.

        Args:
            key: The dependency key

        Returns:
            The resolved dependency

        Raises:
            DependencyNotFoundError: If key not found in this scope
        """
        with self._registry_lock:
            if key in self._cache:
                return self._cache[key]
            if key not in self._registry:
                # Get available keys for suggestions
                available_keys = list(self._registry.keys())
                raise DependencyNotFoundError(key=key, available_keys=available_keys)

            value_or_resolver_with_args = self._registry[key]
            resolver: StoreResolverType
            if isinstance(value_or_resolver_with_args, _StoreResolverWithArgs):
                resolver = value_or_resolver_with_args.resolver
                evaluate_once = value_or_resolver_with_args.evaluate_once
            elif isinstance(value_or_resolver_with_args, _AsyncStoreResolverWithArgs):
                resolver = value_or_resolver_with_args.sync_wrapper
                evaluate_once = value_or_resolver_with_args.evaluate_once
            else:
                return value_or_resolver_with_args

            if evaluate_once:
                resolution_lock = self._resolution_locks.setdefault(key, threading.RLock())

        # Resolvers run outside the registry lock so that resolver code cannot deadlock the scope.
        if not evaluate_once:
            return self._resolve(resolver)

        # The per-key lock keeps an evaluate_once resolver to a single execution.
        with resolution_lock:
            with self._registry_lock:
                if key in self._cache:
                    return self._cache[key]
            result = self._resolve(resolver)
            with self._registry_lock:
                # Skip the cache if the registration was replaced while resolving.
                if self._registry.get(key) is value_or_resolver_with_args:
                    self._cache[key] = result
            return result

    def _resolve(self, resolver: StoreResolverType) -> Any:
        resolver_parameters = _get_parameters(resolver)
        resolver_args: dict[str, Any] = {}

        for param_name, param in resolver_parameters.items():
            if param.default is not inspect.Parameter.empty and isinstance(param.default, Inject):
                resolver_args[param_name] = self._resolve_parameter(param.default.get_inject_key())

        return resolver(**resolver_args)

    def _resolve_parameter(self, key: StoreKeyType) -> Any:
        """Resolve a resolver dependency from active scopes, then from this scope.

        Active scopes come first so that a nested scope keeps overriding, and this
        scope is the fallback so resolvers also work without an active scope.
        """
        try:
            return resolve_dependency(key)
        except DependencyNotFoundError:
            if key in self._registry:
                return self[key]
            raise

    def __setitem__(self, _key: Any, _value: Any) -> None:
        raise InvalidStoreOperationError(
            operation="direct assignment (scope[key] = value)",
            reason="Direct assignment is not allowed to maintain dependency integrity",
        )

    def contains(self, key: StoreKeyType) -> bool:
        """Check if this scope contains a dependency key."""
        return key in self._registry

    def _is_async_resolver(self, key: StoreKeyType) -> bool:
        """Check if a key corresponds to an async resolver."""
        with self._registry_lock:
            # Use cache first for performance
            if key in self._async_resolver_cache:
                return self._async_resolver_cache[key]

            # Fallback to registry check (shouldn't happen in normal cases)
            if key in self._registry:
                is_async = isinstance(self._registry[key], _AsyncStoreResolverWithArgs)
                self._async_resolver_cache[key] = is_async  # Cache the result
                return is_async
            return False

    def __enter__(self) -> "DependencyScope":
        """Sync context manager entry - works for both sync and async contexts."""
        stack = _get_scope_stack()
        new_stack = stack + [self]
        _set_scope_stack(new_stack)
        return self

    def __exit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Sync context manager exit - works for both sync and async contexts.

        Registrations are kept, so the scope can be entered again.
        """
        self._deactivate()

    async def __aenter__(self) -> "DependencyScope":
        """Async context manager entry."""
        stack = _get_scope_stack()
        new_stack = stack + [self]
        _set_scope_stack(new_stack)
        return self

    async def __aexit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Async context manager exit.

        Registrations are kept, so the scope can be entered again.
        """
        self._deactivate()

    def _deactivate(self) -> None:
        """Remove the innermost entry for this scope from the scope stack.

        Scopes exited out of order are removed from their own position, so they
        stop resolving even when another scope is still on top.
        """
        stack = _get_scope_stack()
        for index in reversed(range(len(stack))):
            if stack[index] is self:
                del stack[index]
                _set_scope_stack(stack)
                return

    def is_active(self) -> bool:
        """Check if this scope is on the scope stack of the current context."""
        return any(scope is self for scope in _get_scope_stack())


def resolve_dependency(key: StoreKeyType, additional_scopes: list[DependencyScope] | None = None) -> Any:
    """Resolve a dependency from active scopes and additional scopes.

    Dependencies are resolved in this order:
    1. Additional scopes (if provided, last one wins)
    2. Active scope stack (innermost scope wins)

    Args:
        key: The dependency key to resolve
        additional_scopes: Optional list of additional scopes to search

    Returns:
        The resolved dependency value

    Raises:
        DependencyNotFoundError: If dependency not found in any scope
    """
    # Try additional scopes first (last one wins)
    if additional_scopes:
        for scope in reversed(additional_scopes):
            if scope.contains(key):
                return scope[key]

    # Try active scope stack (innermost wins)
    stack = _get_scope_stack()
    for scope in reversed(stack):
        if scope.contains(key):
            return scope[key]

    # Collect all available keys for better error messages
    available_keys: list[str] = []

    # Collect from additional scopes
    if additional_scopes:
        for scope in additional_scopes:
            available_keys.extend(str(k) for k in scope._registry.keys())

    # Collect from stack scopes
    for scope in stack:
        available_keys.extend(str(k) for k in scope._registry.keys())

    raise DependencyNotFoundError(key=key, available_keys=list(set(available_keys)))


@contextmanager
def dependency_scope() -> Generator[DependencyScope, None, None]:
    """Create a new dependency scope context manager.

    This is a convenience function equivalent to using DependencyScope() directly.

    Example:
        >>> with dependency_scope() as scope:
        ...     scope.register_value("config", {"env": "test"})
        ...     # Use dependencies within this scope
    """
    scope = DependencyScope()
    with scope:
        yield scope


def get_active_scopes() -> list[DependencyScope]:
    """Get all currently active scopes.

    Returns:
        List of active scopes from outermost to innermost
    """
    return _get_scope_stack().copy()


def clear_scope_stack() -> None:
    """Clear the scope stack for the current context (thread or async task).

    This is primarily for testing purposes to ensure clean state.
    """
    _set_scope_stack([])


__all__ = [
    "DependencyScope",
    "dependency_scope",
    "resolve_dependency",
    "get_active_scopes",
    "clear_scope_stack",
    "StoreKeyType",
    "StoreResolverType",
]
