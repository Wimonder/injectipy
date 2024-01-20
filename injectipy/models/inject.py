from typing import Any, Generic, TypeAlias, TypeVar

T = TypeVar("T")
InjectKeyType: TypeAlias = str | type


class _TypingMeta(type):
    def __getitem__(cls, item: Any) -> Any:
        return cls(item)


class _Inject(Generic[T]):
    """Base class for dependency injection markers.

    This class represents a dependency that should be injected at runtime.
    It stores the key used to look up the dependency in the store.

    Args:
        inject_key: The key to use for dependency lookup (string or type)
    """

    _inject_key: InjectKeyType

    def __init__(
        self,
        inject_key: InjectKeyType,
    ) -> None:
        self._inject_key = inject_key

    def get_inject_key(self) -> InjectKeyType:
        return self._inject_key

    def __call__(self) -> T:
        return self  # type: ignore


class Inject(_Inject, metaclass=_TypingMeta):
    """Type-safe dependency injection marker.

    Use this class to mark function parameters that should be automatically
    injected from the dependency store. It supports both string keys and
    type-based keys with full type safety.

    The class uses a metaclass to enable the Inject[key] syntax while
    maintaining type information for static analysis tools like mypy.

    Example:
        >>> from injectipy import inject, Inject, DependencyScope
        >>>
        >>> scope = DependencyScope()
        >>> scope.register_value("api_key", "secret123")
        >>> scope.register_value(str, "default_string")
        >>>
        >>> @inject
        >>> def my_function(
        ...     name: str,
        ...     api_key: str = Inject["api_key"],
        ...     default: str = Inject[str]
        ... ):
        ...     return f"{name}: {api_key}, {default}"
        >>>
        >>> with scope:
        ...     result = my_function("test")

    Type Safety:
        The Inject class maintains type information so that mypy and other
        type checkers can verify that the injected dependency matches the
        parameter type annotation.
    """

    ...


__all__ = ["Inject"]
