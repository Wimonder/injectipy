"""Injectipy - A lightweight, thread-safe dependency injection library for Python.

This package provides a simple yet powerful dependency injection system with:
- Thread-safe singleton pattern
- Circular dependency detection  
- Type safety with mypy support
- Lazy evaluation with optional caching
- Forward reference support

Basic Usage:
    >>> from injectipy import inject, Inject, injectipy_store
    >>> 
    >>> # Register dependencies
    >>> injectipy_store.register_value("config", {"debug": True})
    >>> injectipy_store.register_resolver("logger", lambda: "Logger")
    >>> 
    >>> # Use dependency injection
    >>> @inject
    >>> def my_function(config: dict = Inject["config"]):
    ...     return f"Debug mode: {config['debug']}"
    >>> 
    >>> result = my_function()  # Dependencies automatically injected

Components:
    inject: Decorator for enabling dependency injection on functions
    Inject: Type-safe marker for injectable parameters  
    InjectipyStore: Thread-safe dependency store class
    injectipy_store: Global singleton store instance
"""

from .inject import inject
from .models.inject import Inject
from .store import InjectipyStore, injectipy_store

__all__ = ["inject", "Inject", "InjectipyStore", "injectipy_store"]
