"""Injectipy - A lightweight, thread-safe dependency injection library for Python.

This package provides a simple yet powerful dependency injection system with:
- Explicit dependency scopes with context managers
- Thread-safe scope management
- Circular dependency detection
- Type safety with mypy support
- Lazy evaluation with optional caching
- Forward reference support

Basic Usage:
    >>> from injectipy import inject, Inject, DependencyScope
    >>>
    >>> # Create a dependency scope
    >>> scope = DependencyScope()
    >>> scope.register_value("config", {"debug": True})
    >>> scope.register_resolver("logger", lambda: "Logger")
    >>>
    >>> # Use dependency injection within the scope
    >>> @inject
    >>> def my_function(config: dict = Inject["config"]):
    ...     return f"Debug mode: {config['debug']}"
    >>>
    >>> with scope:
    ...     result = my_function()  # Dependencies automatically injected

Components:
    inject: Decorator for enabling dependency injection on functions
    Inject: Type-safe marker for injectable parameters
    DependencyScope: Thread-safe dependency scope with context manager
    dependency_scope: Convenience function for creating scopes
"""

from .exceptions import (
    CircularDependencyError,
    DependencyError,
    DependencyNotFoundError,
    DuplicateRegistrationError,
    InjectionError,
    InjectipyError,
    InvalidStoreOperationError,
    ParameterValidationError,
    PositionalOnlyInjectionError,
    StoreOperationError,
)
from .inject import inject
from .models.inject import Inject
from .scope import (
    DependencyScope,
    clear_scope_stack,
    dependency_scope,
    get_active_scopes,
    resolve_dependency,
)

__version__ = "0.1.0"
__all__ = [
    "inject",
    "Inject",
    "DependencyScope",
    "dependency_scope",
    "resolve_dependency",
    "get_active_scopes",
    "clear_scope_stack",
    "__version__",
    "InjectipyError",
    "DependencyError",
    "DependencyNotFoundError",
    "CircularDependencyError",
    "DuplicateRegistrationError",
    "ParameterValidationError",
    "InjectionError",
    "PositionalOnlyInjectionError",
    "StoreOperationError",
    "InvalidStoreOperationError",
]
