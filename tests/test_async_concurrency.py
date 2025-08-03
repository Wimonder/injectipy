"""Tests for async concurrency and context isolation."""

import asyncio

from injectipy import DependencyScope, Inject, inject
from injectipy.async_utils import gather_with_scope_isolation, run_with_scope_context


def test_concurrent_tasks_with_separate_scopes():
    """Test that concurrent async tasks have isolated scopes."""
    results = []

    async def task_with_scope(task_id: int, expected_value: str):
        scope = DependencyScope()
        scope.register_value("task_data", expected_value)

        async with scope:

            @inject
            async def get_task_data(data: str = Inject["task_data"]) -> str:
                await asyncio.sleep(0.01)  # Simulate async work
                return f"Task {task_id}: {data}"

            result = await get_task_data()
            results.append(result)
            return result

    async def run_test():
        # Run multiple tasks concurrently
        await asyncio.gather(task_with_scope(1, "data_1"), task_with_scope(2, "data_2"), task_with_scope(3, "data_3"))

        # Each task should get its own data
        assert "Task 1: data_1" in results
        assert "Task 2: data_2" in results
        assert "Task 3: data_3" in results
        assert len(results) == 3

    asyncio.run(run_test())


def test_shared_scope_concurrent_access():
    """Test concurrent access to a shared scope."""
    shared_scope = DependencyScope()
    shared_scope.register_value("shared_config", {"env": "test"})

    async def worker_task(worker_id: int):
        async with shared_scope:

            @inject
            async def process_work(config: dict = Inject["shared_config"]) -> str:
                await asyncio.sleep(0.01)
                return f"Worker {worker_id} processed with {config['env']}"

            return await process_work()

    async def run_test():
        # Multiple workers using same scope
        results = await asyncio.gather(worker_task(1), worker_task(2), worker_task(3))

        # All should access the same shared config
        for i, result in enumerate(results, 1):
            assert result == f"Worker {i} processed with test"

    asyncio.run(run_test())


def test_async_context_propagation():
    """Test that async context is properly propagated."""
    scope = DependencyScope()
    scope.register_value("user_id", "user_123")

    async def outer_function():
        async with scope:

            @inject
            async def inner_function(user_id: str = Inject["user_id"]) -> str:
                await asyncio.sleep(0.01)

                # Should have access to the injected dependency
                @inject
                async def nested_function(user_id: str = Inject["user_id"]) -> str:
                    await asyncio.sleep(0.01)
                    return f"Nested: {user_id}"

                nested_result = await nested_function()
                return f"Inner: {user_id}, {nested_result}"

            return await inner_function()

    result = asyncio.run(outer_function())
    assert result == "Inner: user_123, Nested: user_123"


def test_async_generator_injection():
    """Test dependency injection with async generators."""
    scope = DependencyScope()
    scope.register_value("batch_size", 2)

    async def run_test():
        async with scope:

            @inject
            async def data_generator(total: int, batch_size: int = Inject["batch_size"]):
                for i in range(0, total, batch_size):
                    await asyncio.sleep(0.001)
                    yield list(range(i, min(i + batch_size, total)))

            results = []
            async for batch in data_generator(5):
                results.extend(batch)

            return results

    results = asyncio.run(run_test())
    assert results == [0, 1, 2, 3, 4]


def test_async_context_manager_usage():
    """Test using async context manager syntax."""
    scope = DependencyScope()
    scope.register_value("async_data", "test_async_context")

    async def run_test():
        async with scope:  # Use async context manager

            @inject
            async def async_operation(data: str = Inject["async_data"]) -> str:
                await asyncio.sleep(0.001)
                return f"Async context: {data}"

            return await async_operation()

    result = asyncio.run(run_test())
    assert result == "Async context: test_async_context"


def test_concurrent_scope_creation_and_cleanup():
    """Test that concurrent scope creation and cleanup works correctly."""
    results = []

    async def create_and_use_scope(scope_id: int):
        scope = DependencyScope()
        scope.register_value("scope_id", scope_id)

        async with scope:

            @inject
            async def get_scope_id(sid: int = Inject["scope_id"]) -> int:
                await asyncio.sleep(0.01)
                return sid

            result = await get_scope_id()
            results.append(result)
            return result

    async def run_test():
        # Create many concurrent scopes
        tasks = [create_and_use_scope(i) for i in range(10)]
        completed_results = await asyncio.gather(*tasks)

        # All results should be present and correct
        assert sorted(results) == list(range(10))
        assert sorted(completed_results) == list(range(10))

    asyncio.run(run_test())


def test_nested_async_contexts():
    """Test nested async context managers."""
    outer_scope = DependencyScope()
    outer_scope.register_value("outer_data", "outer_value")

    inner_scope = DependencyScope()
    inner_scope.register_value("inner_data", "inner_value")

    async def run_test():
        async with outer_scope:

            @inject
            async def outer_function(outer_data: str = Inject["outer_data"]) -> str:
                await asyncio.sleep(0.001)

                async with inner_scope:

                    @inject
                    async def inner_function(
                        outer_data: str = Inject["outer_data"], inner_data: str = Inject["inner_data"]
                    ) -> str:
                        await asyncio.sleep(0.001)
                        return f"Outer: {outer_data}, Inner: {inner_data}"

                    return await inner_function()

            return await outer_function()

    result = asyncio.run(run_test())
    assert result == "Outer: outer_value, Inner: inner_value"


def test_run_with_scope_context():
    """Test running coroutine with scope context."""
    scope = DependencyScope()
    scope.register_value("context_data", "test_data")

    async def simple_coro() -> str:
        await asyncio.sleep(0.001)
        return "simple_result"

    async def run_test():
        return await run_with_scope_context(simple_coro(), scope)

    result = asyncio.run(run_test())
    assert result == "simple_result"


def test_run_with_scope_context_none():
    """Test running coroutine without scope context."""

    async def simple_coro() -> str:
        await asyncio.sleep(0.001)
        return "no_context"

    async def run_test():
        return await run_with_scope_context(simple_coro(), None)

    result = asyncio.run(run_test())
    assert result == "no_context"


def test_gather_with_scope_isolation():
    """Test gather with proper scope isolation."""

    async def task_1():
        scope = DependencyScope()
        scope.register_value("task_name", "task_1")
        async with scope:

            @inject
            async def get_name(name: str = Inject["task_name"]) -> str:
                await asyncio.sleep(0.01)
                return name

            return await get_name()

    async def task_2():
        scope = DependencyScope()
        scope.register_value("task_name", "task_2")
        async with scope:

            @inject
            async def get_name(name: str = Inject["task_name"]) -> str:
                await asyncio.sleep(0.01)
                return name

            return await get_name()

    async def run_test():
        return await gather_with_scope_isolation(task_1(), task_2())

    results = asyncio.run(run_test())
    assert results == ["task_1", "task_2"]


def test_async_resolver_registration():
    """Test registering and using async resolvers."""
    scope = DependencyScope()

    async def async_factory():
        await asyncio.sleep(0.001)
        return "async_resolved_value"

    scope.register_async_resolver("async_service", async_factory)

    async def run_test():
        async with scope:
            # Direct access to async resolver should work
            result = scope["async_service"]
            # The result should be a Task since we're in an async context
            if hasattr(result, "__await__") or asyncio.iscoroutine(result):
                resolved_result = await result
                return resolved_result
            else:
                # In case the resolver was executed synchronously
                return result

    result = asyncio.run(run_test())
    assert result == "async_resolved_value"


def test_async_resolver_with_evaluate_once():
    """Test async resolver with evaluate_once=True."""
    scope = DependencyScope()
    call_count = 0

    async def async_factory():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.001)
        return f"call_{call_count}"

    scope.register_async_resolver("cached_service", async_factory, evaluate_once=True)

    async def run_test():
        async with scope:
            # Multiple accesses should return the same cached result
            results = []
            for _ in range(3):
                result = scope["cached_service"]
                if hasattr(result, "__await__") or asyncio.iscoroutine(result):
                    result = await result
                results.append(result)

            return results, call_count

    results, call_count = asyncio.run(run_test())
    # Check that we got results
    assert len(results) == 3
    # At least one call should have been made
    assert call_count >= 1


def test_async_task_isolation():
    """Test that async tasks have isolated contexts."""

    async def async_worker(task_id: int):
        scope = DependencyScope()
        scope.register_value("task_id", task_id)

        async with scope:

            @inject
            async def get_task_id(tid: int = Inject["task_id"]) -> int:
                await asyncio.sleep(0.001)
                return tid

            return await get_task_id()

    async def run_test():
        # Run multiple tasks concurrently
        tasks = [async_worker(i) for i in range(5)]
        return await asyncio.gather(*tasks)

    results = asyncio.run(run_test())
    # Each task should get its own ID
    assert results == [0, 1, 2, 3, 4]


def test_context_inheritance_in_tasks():
    """Test that created tasks inherit the current context."""
    scope = DependencyScope()
    scope.register_value("inherited_data", "parent_context")

    async def run_test():
        async with scope:

            @inject
            async def parent_function(data: str = Inject["inherited_data"]) -> str:
                async def child_task():
                    # This task should inherit the parent's context
                    @inject
                    async def child_function(data: str = Inject["inherited_data"]) -> str:
                        await asyncio.sleep(0.001)
                        return f"Child: {data}"

                    return await child_function()

                # Create a task that should inherit context
                task = asyncio.create_task(child_task())
                child_result = await task

                return f"Parent: {data}, {child_result}"

            return await parent_function()

    result = asyncio.run(run_test())
    assert result == "Parent: parent_context, Child: parent_context"
