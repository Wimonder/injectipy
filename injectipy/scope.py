"""Dependency scope management with context managers for explicit scoping."""

import asyncio
import contextvars
import inspect
import threading
from collections.abc import Callable, Coroutine, Generator
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
_scope_stack: contextvars.ContextVar[list["DependencyScope"]] = contextvars.ContextVar(
    "injectipy_scope_stack", default=[]
)


@dataclass(frozen=True)
class _StoreResolverWithArgs:
    resolver: StoreResolverType
    evaluate_once: bool


_StoreValueType = _StoreResolverWithArgs | Any


def _get_scope_stack() -> list["DependencyScope"]:
    """Get the current scope stack from context variables.

    This works correctly for both threading and asyncio contexts.
    """
    return _scope_stack.get().copy()


def _set_scope_stack(stack: list["DependencyScope"]) -> None:
    """Set the scope stack in the current context."""
    _scope_stack.set(stack)


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
        self._registry_lock = threading.RLock()
        self._active = False

    def register_value(self, key: StoreKeyType, value: Any) -> "DependencyScope":
        """Register a static value in this scope.

        Args:
            key: The dependency key
            value: The value to register

        Returns:
            Self for method chaining

        Raises:
            DuplicateRegistrationError: If key already exists in this scope
        """
        with self._registry_lock:
            self._raise_if_key_already_registered(key)
            self._registry[key] = value
            self._cache[key] = value
        return self

    def register_resolver(
        self, key: StoreKeyType, resolver: StoreResolverType, *, evaluate_once: bool = False
    ) -> "DependencyScope":
        """Register a factory function in this scope.

        Args:
            key: The dependency key
            resolver: Factory function that creates the dependency
            evaluate_once: If True, cache the result after first evaluation

        Returns:
            Self for method chaining

        Raises:
            DuplicateRegistrationError: If key already exists in this scope
            CircularDependencyError: If circular dependency detected
        """
        with self._registry_lock:
            self._raise_if_key_already_registered(key)
            self._check_circular_dependencies(key, resolver)
            self._registry[key] = _StoreResolverWithArgs(resolver, evaluate_once)
        return self

    def register_async_resolver(
        self, key: StoreKeyType, async_resolver: Callable[..., Coroutine[Any, Any, Any]], *, evaluate_once: bool = False
    ) -> "DependencyScope":
        """Register an async factory function.

        Args:
            key: The dependency key
            async_resolver: Async factory function that creates the dependency
            evaluate_once: If True, cache the result after first evaluation

        Returns:
            Self for method chaining

        Raises:
            DuplicateRegistrationError: If key already exists in this scope
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

        return self.register_resolver(key, sync_wrapper, evaluate_once=evaluate_once)

    def _raise_if_key_already_registered(self, key: StoreKeyType) -> None:
        if key in self._registry:
            # Determine the type of existing registration
            existing_entry = self._registry[key]
            existing_type = "resolver" if isinstance(existing_entry, _StoreResolverWithArgs) else "value"
            raise DuplicateRegistrationError(key, existing_type=existing_type)

    def _check_circular_dependencies(self, new_key: StoreKeyType, new_resolver: StoreResolverType) -> None:
        new_dependencies = self._get_resolver_dependencies(new_resolver)

        for dep_key in new_dependencies:
            if self._has_dependency_path(dep_key, new_key, set()):
                dependency_chain = self._build_dependency_chain(dep_key, new_key, [])
                raise CircularDependencyError(
                    dependency_chain=dependency_chain, new_key=new_key, conflicting_key=dep_key
                )

    def _get_resolver_dependencies(self, resolver: StoreResolverType) -> set[StoreKeyType]:
        dependencies = set()
        resolver_signature = inspect.signature(resolver)

        for param in resolver_signature.parameters.values():
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

        return current_chain + [from_key]

    @overload
    def __getitem__(self, key: str) -> Any:
        ...

    @overload
    def __getitem__(self, key: type[T]) -> T:
        ...

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
            if key in self._registry:
                value_or_resolver_with_args = self._registry[key]

                result: Any
                if isinstance(value_or_resolver_with_args, _StoreResolverWithArgs):
                    resolver_with_args = value_or_resolver_with_args
                    result = self._resolve(resolver_with_args.resolver)
                    if resolver_with_args.evaluate_once:
                        self._cache[key] = result
                else:
                    result = value_or_resolver_with_args

                return result
            # Get available keys for suggestions
            available_keys = list(self._registry.keys())
            raise DependencyNotFoundError(key=key, available_keys=available_keys)

    def _resolve(self, resolver: StoreResolverType) -> Any:
        resolver_signature = inspect.signature(resolver)
        resolver_parameters = resolver_signature.parameters
        resolver_args: dict[str, Any] = {}

        for param_name, param in resolver_parameters.items():
            if param.default is not inspect.Parameter.empty and isinstance(param.default, Inject):
                try:
                    resolver_args[param_name] = resolve_dependency(param.default.get_inject_key())
                except DependencyNotFoundError:
                    # If the dependency is not found and param has no default, this will cause an error
                    # Let the resolver handle missing dependencies by falling back to the Inject object
                    pass

        return resolver(**resolver_args)

    def __setitem__(self, _key: Any, _value: Any) -> None:
        raise InvalidStoreOperationError(
            operation="direct assignment (scope[key] = value)",
            reason="Direct assignment is not allowed to maintain dependency integrity",
        )

    def contains(self, key: StoreKeyType) -> bool:
        """Check if this scope contains a dependency key."""
        return key in self._registry

    def __enter__(self) -> "DependencyScope":
        """Sync context manager entry - works for both sync and async contexts."""
        stack = _get_scope_stack()
        new_stack = stack + [self]
        _set_scope_stack(new_stack)
        self._active = True
        return self

    def __exit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Sync context manager exit - works for both sync and async contexts."""
        stack = _get_scope_stack()
        if stack and stack[-1] is self:
            new_stack = stack[:-1]
            _set_scope_stack(new_stack)
        self._active = False
        with self._registry_lock:
            self._registry.clear()
            self._cache.clear()

    async def __aenter__(self) -> "DependencyScope":
        """Async context manager entry."""
        stack = _get_scope_stack()
        new_stack = stack + [self]
        _set_scope_stack(new_stack)
        self._active = True
        return self

    async def __aexit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Async context manager exit with cleanup."""
        stack = _get_scope_stack()
        if stack and stack[-1] is self:
            new_stack = stack[:-1]
            _set_scope_stack(new_stack)
        self._active = False
        # Use regular synchronous cleanup - registry operations are already thread-safe
        with self._registry_lock:
            self._registry.clear()
            self._cache.clear()

    def is_active(self) -> bool:
        """Check if this scope is currently active."""
        return self._active

    def _reset_for_testing(self) -> None:
        """Reset the scope state for testing purposes only."""
        with self._registry_lock:
            self._registry.clear()
            self._cache.clear()


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
