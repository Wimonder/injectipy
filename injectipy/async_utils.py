"""Async utilities for dependency injection in asyncio contexts."""

import asyncio
import contextvars
from collections.abc import Coroutine
from typing import Any, TypeVar

from injectipy.scope import DependencyScope

T = TypeVar("T")


async def run_with_scope_context(coro: Coroutine[Any, Any, T], scope: DependencyScope | None = None) -> T:
    """Run a coroutine with proper scope context propagation.

    Args:
        coro: The coroutine to run
        scope: Optional scope to use for the coroutine

    Returns:
        The coroutine result with proper context isolation
    """
    if scope is not None:
        async with scope:
            return await coro
    else:
        return await coro


async def gather_with_scope_isolation(*coros: Coroutine[Any, Any, Any]) -> list[Any]:
    """Run multiple coroutines with proper scope isolation.

    Each coroutine gets its own scope context to prevent interference.

    Args:
        *coros: The coroutines to run with isolation

    Returns:
        List of results from each coroutine
    """

    async def isolated_coro(coro: Coroutine[Any, Any, Any]) -> Any:
        # Each coroutine runs in its own context
        ctx = contextvars.copy_context()

        def run_in_context() -> asyncio.Task[Any]:
            return asyncio.create_task(coro)

        task = ctx.run(run_in_context)
        return await task

    return await asyncio.gather(*[isolated_coro(coro) for coro in coros])


__all__ = [
    "run_with_scope_context",
    "gather_with_scope_isolation",
]
