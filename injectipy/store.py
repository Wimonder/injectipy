import inspect
import threading
from dataclasses import dataclass
from typing import Any, Callable, TypeVar, Union, overload

from typing_extensions import TypeAlias

from injectipy.models.inject import Inject

_ParamNameType: TypeAlias = str
_ParamType: TypeAlias = type
StoreKeyType = Union[_ParamNameType, _ParamType]
StoreResolverType = Callable[..., Any]


@dataclass(frozen=True)
class _StoreResolverWithArgs:
    resolver: StoreResolverType
    evaluate_once: bool


_StoreValueType = Union[_StoreResolverWithArgs, Any]

T = TypeVar("T")


class InjectipyStore:
    """Thread-safe singleton dependency injection store.

    This class manages dependency registration and resolution with support for:
    - Thread-safe singleton pattern with proper locking
    - Circular dependency detection
    - Lazy evaluation with optional caching
    - Type-safe dependency resolution

    The store supports two types of dependencies:
    1. Values: Static objects registered with register_value()
    2. Resolvers: Factory functions registered with register_resolver()

    Example:
        >>> store = InjectipyStore()
        >>> store.register_value("config", {"debug": True})
        >>> store.register_resolver("logger", lambda: "Logger instance")
        >>> config = store["config"]  # {"debug": True}
        >>> logger = store["logger"]  # "Logger instance"
    """

    _instance: "InjectipyStore | None" = None
    _lock: threading.Lock = threading.Lock()
    _registry: dict[StoreKeyType, _StoreValueType]
    _cache: dict[StoreKeyType, Any]
    _registry_lock: threading.RLock

    def __new__(cls) -> "InjectipyStore":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if not getattr(self, "_initialized", False):
            self._registry = {}
            self._cache = {}
            self._registry_lock = threading.RLock()
            self._initialized = True

    def register_resolver(
        self,
        key: StoreKeyType,
        resolver: StoreResolverType,
        *,
        evaluate_once: bool = False,
    ) -> None:
        """Register a factory function as a dependency resolver.

        The resolver function will be called to create the dependency value when
        requested. Dependencies can be injected into the resolver using Inject[key] annotations.

        Args:
            key: Unique identifier for this dependency
            resolver: Factory function that creates the dependency
            evaluate_once: If True, cache the result after first evaluation
                         (singleton pattern). Defaults to False.

        Raises:
            ValueError: If key is already registered or circular dependency detected
            TypeError: If resolver has unsupported parameter types

        Example:
            >>> def create_database(host: str = Inject["db_host"]):
            ...     return f"Database({host})"
            >>> store.register_resolver("database", create_database)
            >>> store.register_resolver("cache", lambda: "Redis", evaluate_once=True)
        """
        with self._registry_lock:
            self._raise_if_key_already_registered(key)
            self._validate_resolver_signature(key, resolver)

            # Check for circular dependencies
            self._check_circular_dependencies(key, resolver)

            self._registry[key] = _StoreResolverWithArgs(resolver, evaluate_once)

    def _validate_resolver_signature(self, resolver_key: StoreKeyType, resolver: StoreResolverType) -> None:
        resolver_signature = inspect.signature(resolver)
        resolver_parameters = resolver_signature.parameters
        for param in resolver_parameters.values():
            if param.kind not in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                raise ValueError(
                    f"Resolver {resolver_key} has unsupported parameter kind {param.kind} for parameter {param.name}"
                )

            # Note: We now allow forward references - dependencies will be validated at resolution time
            # This allows us to register resolvers in any order and detect circular dependencies

    def register_value(self, key: StoreKeyType, value: Any) -> None:
        """Register a static value as a dependency.

        The value will be returned as-is when requested from the store.
        This is useful for configuration values, constants, or pre-built objects.

        Args:
            key: Unique identifier for this dependency
            value: The static value to register

        Raises:
            ValueError: If key is already registered

        Example:
            >>> store.register_value("api_key", "secret123")
            >>> store.register_value("database", DatabaseConnection())
            >>> api_key = store["api_key"]  # "secret123"
        """
        with self._registry_lock:
            self._raise_if_key_already_registered(key)
            self._registry[key] = value
            self._cache[key] = value

    def _raise_if_key_already_registered(self, key: StoreKeyType) -> None:
        if key in self._registry:
            raise ValueError(f"Key {key} already registered")

    def _check_circular_dependencies(self, new_key: StoreKeyType, new_resolver: StoreResolverType) -> None:
        """Check if adding this resolver would create a circular dependency."""
        # Get dependencies of the new resolver
        new_dependencies = self._get_resolver_dependencies(new_resolver)

        # For each dependency, check if it eventually depends on new_key
        for dep_key in new_dependencies:
            if self._has_dependency_path(dep_key, new_key, set()):
                raise ValueError(f"Circular dependency detected: {new_key} -> {dep_key} -> ... -> {new_key}")

    def _get_resolver_dependencies(self, resolver: StoreResolverType) -> set[StoreKeyType]:
        """Extract all dependencies from a resolver function."""
        dependencies = set()
        resolver_signature = inspect.signature(resolver)

        for param in resolver_signature.parameters.values():
            if param.default is not inspect.Parameter.empty and isinstance(param.default, Inject):
                dependencies.add(param.default.get_inject_key())

        return dependencies

    def _has_dependency_path(self, from_key: StoreKeyType, to_key: StoreKeyType, visited: set[StoreKeyType]) -> bool:
        """Check if there's a dependency path from from_key to to_key."""
        if from_key == to_key:
            return True

        if from_key in visited:
            return False  # Already checked this path

        if from_key not in self._registry:
            return False  # Key doesn't exist, no dependency path

        visited.add(from_key)

        # Get the dependencies of from_key
        registry_entry = self._registry[from_key]
        if isinstance(registry_entry, _StoreResolverWithArgs):
            dependencies = self._get_resolver_dependencies(registry_entry.resolver)
            for dep_key in dependencies:
                if self._has_dependency_path(dep_key, to_key, visited.copy()):
                    return True

        return False

    def __setitem__(self, key: Any, value: Any) -> None:
        raise NotImplementedError("Use register_resolver or register_value instead")

    @overload
    def __getitem__(self, key: _ParamNameType) -> Any:
        ...

    @overload
    def __getitem__(self, key: type[T]) -> T:
        ...

    def __getitem__(self, key: Any) -> Any:
        """Resolve and return a dependency by key.

        This method resolves dependencies on-demand:
        - For registered values: returns the value directly
        - For resolvers: calls the factory function with injected dependencies
        - For cached resolvers (evaluate_once=True): returns cached result

        Args:
            key: The dependency key to resolve

        Returns:
            The resolved dependency value

        Raises:
            KeyError: If the key is not registered in the store
            TypeError: If resolver function is missing required arguments

        Example:
            >>> store.register_value("config", {"debug": True})
            >>> config = store["config"]  # {"debug": True}
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
            raise KeyError(f"Key {key} not found in the store")

    def _resolve(
        self,
        resolver: StoreResolverType,
    ) -> Any:
        resolver_signature = inspect.signature(resolver)
        resolver_parameters = resolver_signature.parameters
        resolver_args: dict[str, Any] = {}

        for param_name, param in resolver_parameters.items():
            if param.default is not inspect.Parameter.empty and isinstance(param.default, Inject):
                try:
                    resolver_args[param_name] = self[param.default.get_inject_key()]
                except KeyError:
                    # If the dependency is not found and param has no default, this will cause an error
                    # Let the resolver handle missing dependencies
                    pass

        return resolver(**resolver_args)

    def _reset_for_testing(self) -> None:
        """Reset the store state for testing purposes only.

        This method clears all registered dependencies and cached values.
        It should only be used in test environments to ensure test isolation.

        Warning:
            This method is intended for testing only and should not be used
            in production code as it affects the global singleton state.

        Example:
            >>> # In pytest fixture
            >>> @pytest.fixture(autouse=True)
            >>> def reset_store():
            ...     injectipy_store._reset_for_testing()
        """
        with self._registry_lock:
            self._registry.clear()
            self._cache.clear()


injectipy_store = InjectipyStore()


__all__ = ["InjectipyStore", "injectipy_store"]
