"""Tests for the @ainject decorator."""

import asyncio
from typing import Protocol

import pytest

from injectipy import DependencyScope, Inject, ainject, inject
from injectipy.exceptions import DependencyNotFoundError, PositionalOnlyInjectionError


class AsyncApiClient(Protocol):
    async def fetch(self, endpoint: str) -> dict:
        ...


class MockAsyncApiClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def fetch(self, endpoint: str) -> dict:
        await asyncio.sleep(0.01)  # Simulate async operation
        return {
            "endpoint": f"{self.base_url}{endpoint}",
            "authenticated": bool(self.api_key),
            "data": f"response from {endpoint}",
        }


async def create_async_api_client(base_url: str, api_key: str) -> MockAsyncApiClient:
    """Async factory for creating API clients."""
    await asyncio.sleep(0.01)  # Simulate async initialization
    return MockAsyncApiClient(base_url, api_key)


def test_ainject_with_sync_dependency():
    """Test ainject with synchronous dependencies."""
    scope = DependencyScope()
    scope.register_value("config", {"debug": True})

    @ainject
    async def get_config(config: dict = Inject["config"]) -> dict:
        return config

    async def run_test():
        async with scope:
            result = await get_config()
            assert result == {"debug": True}

    asyncio.run(run_test())


def test_ainject_with_async_dependency():
    """Test ainject with asynchronous dependencies - eliminates hasattr check."""
    scope = DependencyScope()
    scope.register_value("base_url", "https://api.example.com")
    scope.register_value("api_key", "test-key")

    # Need to use inject decorator for proper dependency resolution
    @inject
    async def async_client_factory(
        base_url: str = Inject["base_url"], api_key: str = Inject["api_key"]
    ) -> MockAsyncApiClient:
        return await create_async_api_client(base_url, api_key)

    scope.register_async_resolver(AsyncApiClient, async_client_factory)

    @ainject
    async def fetch_data(endpoint: str, client: AsyncApiClient = Inject[AsyncApiClient]) -> dict:
        # client should be the resolved MockAsyncApiClient, not a Task
        # No need for hasattr(..., '__await__') check!
        assert isinstance(client, MockAsyncApiClient)
        return await client.fetch(endpoint)

    async def run_test():
        async with scope:
            result = await fetch_data("/users")
            expected = {
                "endpoint": "https://api.example.com/users",
                "authenticated": True,
                "data": "response from /users",
            }
            assert result == expected

    asyncio.run(run_test())


def test_ainject_with_mixed_dependencies():
    """Test ainject with both sync and async dependencies."""
    scope = DependencyScope()
    scope.register_value("timeout", 30)  # Sync dependency
    scope.register_value("base_url", "https://api.example.com")
    scope.register_value("api_key", "test-key")

    # Async dependency with proper injection
    @inject
    async def client_factory(
        base_url: str = Inject["base_url"], api_key: str = Inject["api_key"]
    ) -> MockAsyncApiClient:
        return await create_async_api_client(base_url, api_key)

    scope.register_async_resolver("client", client_factory)

    @ainject
    async def process_request(
        endpoint: str, timeout: int = Inject["timeout"], client: MockAsyncApiClient = Inject["client"]
    ) -> dict:
        assert timeout == 30  # Sync dependency resolved
        assert isinstance(client, MockAsyncApiClient)  # Async dependency resolved
        return {"timeout": timeout, "result": await client.fetch(endpoint)}

    async def run_test():
        async with scope:
            result = await process_request("/data")
            assert result["timeout"] == 30
            assert "result" in result

    asyncio.run(run_test())


def test_ainject_explicit_args_override_injection(basic_scope):
    """Test that explicit arguments override dependency injection."""

    @ainject
    async def get_service(service: str = Inject["service"]) -> str:
        return service

    async def run_test():
        async with basic_scope:
            # Should use injected value
            result1 = await get_service()
            assert result1 == "injected_service"

            # Should use explicit value
            result2 = await get_service(service="explicit_service")
            assert result2 == "explicit_service"

    asyncio.run(run_test())


def test_ainject_without_dependencies():
    """Test that ainject works on functions without injectable dependencies."""

    @ainject
    async def simple_function(x: int, y: int) -> int:
        return x + y

    async def run_test():
        result = await simple_function(2, 3)
        assert result == 5

    asyncio.run(run_test())


def test_ainject_with_explicit_scopes():
    """Test ainject using explicit scopes parameter."""
    explicit_scope = DependencyScope()
    explicit_scope.register_value("service_name", "ExplicitService")

    @ainject(scopes=[explicit_scope])
    async def get_service_name(service_name: str = Inject["service_name"]) -> str:
        return service_name

    async def run_test():
        # Should work without active scope context
        result = await get_service_name()
        assert result == "ExplicitService"

    asyncio.run(run_test())


def test_explicit_scopes_override_active_scopes():
    """Test that explicit scopes take precedence over active scopes."""
    active_scope = DependencyScope()
    active_scope.register_value("value", "from_active")

    explicit_scope = DependencyScope()
    explicit_scope.register_value("value", "from_explicit")

    @ainject(scopes=[explicit_scope])
    async def get_value(value: str = Inject["value"]) -> str:
        return value

    async def run_test():
        async with active_scope:
            result = await get_value()
            assert result == "from_explicit"

    asyncio.run(run_test())


def test_ainject_requires_async_function():
    """Test that ainject raises TypeError for non-async functions."""
    with pytest.raises(TypeError, match="@ainject can only be used with async functions"):

        @ainject
        def sync_function():  # Not async
            return "sync"


def test_dependency_not_found_error():
    """Test DependencyNotFoundError is raised for missing dependencies."""

    @ainject
    async def missing_dependency(value: str = Inject["missing"]) -> str:
        return value

    async def run_test():
        with pytest.raises(DependencyNotFoundError, match="missing"):
            await missing_dependency()

    asyncio.run(run_test())


def test_positional_only_injection_error():
    """Test PositionalOnlyInjectionError for positional-only parameters."""
    scope = DependencyScope()
    scope.register_value("value", "test")

    @ainject
    async def func_with_positional_only(value: str = Inject["value"], /) -> str:  # Positional-only
        return value

    async def run_test():
        async with scope:
            with pytest.raises(PositionalOnlyInjectionError):
                await func_with_positional_only()

    asyncio.run(run_test())


def test_ainject_with_classmethod(basic_scope):
    """Test ainject decorator with classmethods."""

    class TestClass:
        @classmethod
        @ainject
        async def get_service(cls, service: str = Inject["service"]) -> str:
            return f"class: {cls.__name__}, service: {service}"

    async def run_test():
        async with basic_scope:
            result = await TestClass.get_service()
            assert result == "class: TestClass, service: injected_service"

    asyncio.run(run_test())


def test_ainject_with_staticmethod(basic_scope):
    """Test ainject decorator with staticmethods."""

    class TestClass:
        @staticmethod
        @ainject
        async def get_service(service: str = Inject["service"]) -> str:
            return f"static: {service}"

    async def run_test():
        async with basic_scope:
            result = await TestClass.get_service()
            assert result == "static: injected_service"

    asyncio.run(run_test())


def test_nested_async_dependencies():
    """Test ainject with nested async dependencies using ainject for nested resolvers."""
    scope = DependencyScope()

    async def create_db_connection():
        await asyncio.sleep(0.01)
        return {"connection": "db://localhost", "connected": True}

    # Use ainject for the service factory to properly handle async dependencies
    @ainject
    async def create_service(db: dict = Inject["db"]):
        # db will be properly awaited by ainject decorator
        await asyncio.sleep(0.01)
        return {"service": "DataService", "db": db}

    scope.register_async_resolver("db", create_db_connection)
    scope.register_async_resolver("service", create_service)

    @ainject
    async def process_data(service: dict = Inject["service"]) -> dict:
        # service should be fully resolved with nested dependencies
        assert isinstance(service["db"], dict)
        assert service["db"]["connected"] is True
        return service

    async def run_test():
        async with scope:
            result = await process_data()
            assert result["service"] == "DataService"
            assert result["db"]["connection"] == "db://localhost"

    asyncio.run(run_test())


def test_concurrent_ainject_calls():
    """Test concurrent calls to ainject-decorated functions."""
    scope = DependencyScope()

    async def create_client(client_id: int):
        await asyncio.sleep(0.01)
        return {"id": client_id, "status": "ready"}

    scope.register_async_resolver("client_1", lambda: create_client(1))
    scope.register_async_resolver("client_2", lambda: create_client(2))

    @ainject
    async def process_with_client_1(client: dict = Inject["client_1"]) -> str:
        return f"Processed by client {client['id']}"

    @ainject
    async def process_with_client_2(client: dict = Inject["client_2"]) -> str:
        return f"Processed by client {client['id']}"

    async def run_test():
        async with scope:
            # Run concurrently
            results = await asyncio.gather(
                process_with_client_1(),
                process_with_client_2(),
            )

            assert results[0] == "Processed by client 1"
            assert results[1] == "Processed by client 2"

    asyncio.run(run_test())


def test_ainject_with_evaluate_once():
    """Test ainject with evaluate_once=True for singleton behavior."""
    scope = DependencyScope()
    creation_count = 0

    async def create_expensive_resource():
        nonlocal creation_count
        creation_count += 1
        await asyncio.sleep(0.01)
        return {"resource_id": creation_count, "expensive": True}

    scope.register_async_resolver("resource", create_expensive_resource, evaluate_once=True)

    @ainject
    async def use_resource(resource: dict = Inject["resource"]) -> int:
        return resource["resource_id"]

    async def run_test():
        async with scope:
            # Call multiple times
            result1 = await use_resource()
            result2 = await use_resource()
            result3 = await use_resource()

            # Should all return the same resource_id (singleton behavior)
            assert result1 == result2 == result3 == 1
            assert creation_count == 1  # Only created once

    asyncio.run(run_test())
