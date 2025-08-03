#!/usr/bin/env python3
"""
Async/await patterns with injectipy.

This example demonstrates:
- Async context managers
- Async resolvers with @ainject (new!) vs @inject
- Concurrent async tasks with proper isolation
- Mixed sync/async dependency resolution
- How @ainject eliminates manual hasattr(..., '__await__') checks

Key Difference:
- @inject: Rejects async dependencies with clear error messages (use @ainject instead)
- @ainject: Automatically awaits async dependencies before function execution
"""

import asyncio
from typing import Protocol

from injectipy import DependencyScope, Inject, ainject, inject


class AsyncApiClient(Protocol):
    async def fetch(self, endpoint: str) -> dict:
        ...


class HttpApiClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def fetch(self, endpoint: str) -> dict:
        # Simulate async HTTP request
        await asyncio.sleep(0.1)
        return {
            "endpoint": f"{self.base_url}{endpoint}",
            "authenticated": bool(self.api_key),
            "data": f"response from {endpoint}",
        }


@inject
async def async_client_factory(base_url: str = Inject["base_url"], api_key: str = Inject["api_key"]) -> HttpApiClient:
    """Async factory function for creating API clients."""
    await asyncio.sleep(0.05)  # Simulate async initialization
    print(f"Creating async API client for {base_url}")
    return HttpApiClient(base_url, api_key)


@ainject  # Use ainject to eliminate hasattr check!
async def fetch_user_data(user_id: int, client: AsyncApiClient = Inject[AsyncApiClient]) -> dict:
    """Fetch user data using injected async API client."""
    # No need for hasattr(..., '__await__') check with ainject!
    # client is already resolved and ready to use
    return await client.fetch(f"/users/{user_id}")


@ainject  # Use ainject for clean async dependency injection
async def fetch_order_data(order_id: int, client: AsyncApiClient = Inject[AsyncApiClient]) -> dict:
    """Fetch order data using injected async API client."""
    # Clean code with ainject - no manual await checks needed!
    return await client.fetch(f"/orders/{order_id}")


async def demonstrate_inject_vs_ainject():
    """Demonstrate the difference between @inject and @ainject for async dependencies."""
    print("=== @inject vs @ainject Comparison ===")

    scope = DependencyScope()
    scope.register_value("base_url", "https://api.example.com")
    scope.register_value("api_key", "demo-key")
    scope.register_async_resolver(AsyncApiClient, async_client_factory, evaluate_once=True)

    # OLD WAY: Using @inject (requires manual checks)
    @inject
    async def old_way_fetch_data(endpoint: str, client: AsyncApiClient = Inject[AsyncApiClient]) -> dict:
        print("OLD: Using @inject - need to check if client is awaitable")
        # Manual check required because @inject returns Task objects for async deps
        if hasattr(client, "__await__"):
            print("OLD: Client is a Task, need to await it manually")
            client = await client
        else:
            print("OLD: Client is already resolved")
        return await client.fetch(endpoint)

    # NEW WAY: Using @ainject (clean and simple)
    @ainject
    async def new_way_fetch_data(endpoint: str, client: AsyncApiClient = Inject[AsyncApiClient]) -> dict:
        print("NEW: Using @ainject - client is pre-resolved!")
        # No manual checks needed! @ainject pre-awaits all async dependencies
        return await client.fetch(endpoint)

    async with scope:
        print("\n--- Testing OLD way with @inject ---")
        try:
            old_result = await old_way_fetch_data("/data")
            print(f"OLD result: {old_result['endpoint']}")
        except Exception as e:
            print(f"OLD: ❌ Error as expected: {type(e).__name__}")
            print("OLD: The error message guides us to use @ainject!")

        print("\n--- Testing NEW way with @ainject ---")
        new_result = await new_way_fetch_data("/data")
        print(f"NEW: ✅ Success! Result: {new_result['endpoint']}")

        print("\n✨ @ainject eliminates errors and makes async DI clean!")

    print()


async def demonstrate_async_context_manager():
    """Demonstrate async context manager usage."""
    print("=== Async Context Manager Demo ===")

    scope = DependencyScope()
    scope.register_value("base_url", "https://api.example.com")
    scope.register_value("api_key", "test-key-123")
    scope.register_async_resolver(AsyncApiClient, async_client_factory, evaluate_once=True)

    async with scope:  # Use async context manager
        print("Fetching user data...")
        user_data = await fetch_user_data(42)
        print(f"User data: {user_data}")

        print("Fetching order data...")
        order_data = await fetch_order_data(123)
        print(f"Order data: {order_data}")

    print("Async context manager demo complete!\n")


async def demonstrate_concurrent_tasks():
    """Demonstrate concurrent async tasks with proper isolation."""
    print("=== Concurrent Tasks Demo ===")

    async def task_with_scope(task_id: int, base_url: str):
        # Each task gets its own scope for isolation
        task_scope = DependencyScope()
        task_scope.register_value("base_url", base_url)
        task_scope.register_value("api_key", f"key-{task_id}")
        task_scope.register_async_resolver(AsyncApiClient, async_client_factory)

        async with task_scope:

            @ainject  # Clean async injection without hasattr checks
            async def process_task(client: AsyncApiClient = Inject[AsyncApiClient]) -> str:
                # client is pre-resolved by ainject - no manual checks needed!
                data = await client.fetch(f"/task/{task_id}")
                return f"Task {task_id} completed: {data['endpoint']}"

            return await process_task()

    # Run multiple tasks concurrently with proper isolation
    print("Starting concurrent tasks...")
    results = await asyncio.gather(
        task_with_scope(1, "https://api1.example.com"),
        task_with_scope(2, "https://api2.example.com"),
        task_with_scope(3, "https://api3.example.com"),
    )

    for result in results:
        print(f"Result: {result}")

    print("Concurrent tasks demo complete!\n")


async def demonstrate_mixed_sync_async():
    """Demonstrate mixing sync and async dependencies."""
    print("=== Mixed Sync/Async Demo ===")

    # Sync configuration
    config = {"timeout": 30, "retries": 3}

    # Async database connection simulator
    async def create_db_connection():
        await asyncio.sleep(0.1)  # Simulate connection setup
        return {"connection": "postgresql://localhost:5432/mydb", "connected": True}

    scope = DependencyScope()
    scope.register_value("config", config)  # Sync dependency
    scope.register_async_resolver("db", create_db_connection)  # Async dependency

    @ainject  # Handles mixed sync/async dependencies seamlessly
    async def process_data(
        data: str, config: dict = Inject["config"], db: dict = Inject["db"]  # Mixed sync/async deps
    ) -> dict:
        print(f"Processing {data} with config: {config}")
        # ainject pre-resolves async dependencies - db is ready to use!
        print(f"Using database: {db['connection']}")
        return {"processed": data, "config": config, "db": db}

    async with scope:
        result = await process_data("user_data")
        print(f"Processing result: {result}")

    print("Mixed sync/async demo complete!\n")


async def main():
    """Run all async pattern demonstrations."""
    print("🚀 Injectipy Async Patterns Demo\n")

    await demonstrate_inject_vs_ainject()
    await demonstrate_async_context_manager()
    await demonstrate_concurrent_tasks()
    await demonstrate_mixed_sync_async()

    print("✨ All async patterns demonstrated successfully!")


if __name__ == "__main__":
    asyncio.run(main())
