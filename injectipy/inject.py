import functools
from typing import Any, Callable, TypeVar, cast

from injectipy.models.inject import Inject
from injectipy.store import injectipy_store

F = TypeVar("F", bound=Callable[..., Any])


def inject(fn: F) -> F:
    original_defaults = fn.__defaults__

    if not original_defaults or all(not isinstance(default, Inject) for default in original_defaults):
        return fn

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        new_defaults = []
        for default in original_defaults:
            if isinstance(default, Inject):
                inject_key = default.get_inject_key()
                try:
                    value = injectipy_store[inject_key]
                except KeyError:
                    raise RuntimeError(f"Could not resolve {inject_key} for {fn.__name__} in module {fn.__module__}")
                new_defaults.append(value)
            else:
                new_defaults.append(default)

        fn.__defaults__ = tuple(new_defaults)

        return_value = fn(*args, **kwargs)

        fn.__defaults__ = original_defaults

        return return_value

    return cast(F, wrapper)


__all__ = ["inject"]
