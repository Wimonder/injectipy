import functools
from typing import Any, Callable, TypeVar, cast

from injectipy.models.inject import Inject
from injectipy.store import injectipy_store

F = TypeVar("F", bound=Callable[..., Any])


def inject(fn: F) -> F:
    """Decorator to enable automatic dependency injection for function parameters.

    This decorator scans function parameters for Inject[key] annotations and
    automatically resolves those dependencies from the global injectipy_store
    when the function is called.

    The decorator preserves the original function signature and only affects
    parameters that have Inject[key] default values. Regular parameters and
    arguments passed explicitly are handled normally.

    Supports both regular parameters and keyword-only parameters with Inject defaults.

    Args:
        fn: The function to decorate

    Returns:
        The decorated function with dependency injection enabled

    Raises:
        RuntimeError: If a required dependency cannot be resolved from the store

    Example:
        >>> from injectipy import inject, Inject, injectipy_store
        >>> injectipy_store.register_value("config", {"debug": True})
        >>>
        >>> @inject
        >>> def my_function(name: str, config: dict = Inject["config"]):
        ...     return f"Hello {name}, debug={config['debug']}"
        >>>
        >>> result = my_function("Alice")  # config automatically injected
        >>> print(result)  # "Hello Alice, debug=True"

    Note:
        - Only parameters with Inject[key] defaults are injected
        - Explicitly passed arguments always override injection
        - The function can be called normally with all parameters if needed
        - Supports both regular and keyword-only parameters
    """
    original_defaults = fn.__defaults__
    original_kwdefaults = fn.__kwdefaults__

    # Check if there are any Inject defaults in either regular or keyword-only parameters
    has_inject_defaults = False

    if original_defaults:
        has_inject_defaults = any(isinstance(default, Inject) for default in original_defaults)

    if original_kwdefaults:
        has_inject_defaults = has_inject_defaults or any(
            isinstance(default, Inject) for default in original_kwdefaults.values()
        )

    if not has_inject_defaults:
        return fn

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Handle regular parameter defaults (__defaults__)
        if original_defaults:
            new_defaults = []
            for default in original_defaults:
                if isinstance(default, Inject):
                    inject_key = default.get_inject_key()
                    try:
                        value = injectipy_store[inject_key]
                    except KeyError as e:
                        raise RuntimeError(
                            f"Could not resolve {inject_key} for {fn.__name__} in module {fn.__module__}"
                        ) from e
                    new_defaults.append(value)
                else:
                    new_defaults.append(default)
            fn.__defaults__ = tuple(new_defaults)

        # Handle keyword-only parameter defaults (__kwdefaults__)
        if original_kwdefaults:
            new_kwdefaults = {}
            for param_name, default in original_kwdefaults.items():
                if isinstance(default, Inject):
                    inject_key = default.get_inject_key()
                    try:
                        value = injectipy_store[inject_key]
                    except KeyError as e:
                        raise RuntimeError(
                            f"Could not resolve {inject_key} for {fn.__name__} in module {fn.__module__}"
                        ) from e
                    new_kwdefaults[param_name] = value
                else:
                    new_kwdefaults[param_name] = default
            fn.__kwdefaults__ = new_kwdefaults

        try:
            return_value = fn(*args, **kwargs)
        finally:
            # Always restore original defaults, even if function raises an exception
            fn.__defaults__ = original_defaults
            fn.__kwdefaults__ = original_kwdefaults

        return return_value

    return cast(F, wrapper)


__all__ = ["inject"]
