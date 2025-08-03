"""Tests for AsyncDependencyError - ensuring @inject rejects async dependencies."""

import asyncio
from typing import Protocol

import pytest

from injectipy import AsyncDependencyError, DependencyScope, Inject, ainject, inject


class AsyncApiClient(Protocol):
    async def fetch(self, endpoint: str) -> dict:
        ...


class MockAsyncApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def fetch(self, endpoint: str) -> dict:
        await asyncio.sleep(0.01)
        return {"endpoint": f"{self.base_url}{endpoint}", "data": "response"}


async def create_async_client(base_url: str) -> MockAsyncApiClient:
    """Async factory for creating API clients."""
    await asyncio.sleep(0.01)
    return MockAsyncApiClient(base_url)


def test_inject_with_async_resolver_raises_error():
    """Test that @inject raises AsyncDependencyError when used with async resolvers."""
    scope = DependencyScope()
    scope.register_value("base_url", "https://api.example.com")
    scope.register_async_resolver("api_client", lambda: create_async_client("https://api.example.com"))

    @inject
    def sync_function_with_async_dep(client: MockAsyncApiClient = Inject["api_client"]) -> str:
        return f"Using client: {client.base_url}"

    with scope:
        with pytest.raises(AsyncDependencyError) as exc_info:
            sync_function_with_async_dep()

        error = exc_info.value
        assert error.function_name == "sync_function_with_async_dep"
        assert error.parameter_name == "client"
        assert error.dependency_key == "api_client"
        assert "Cannot use @inject with async dependency" in str(error)
        assert "Use @ainject instead" in str(error)


def test_inject_with_async_resolver_in_async_function_raises_error():
    """Test that @inject raises AsyncDependencyError even in async functions."""
    scope = DependencyScope()
    scope.register_value("base_url", "https://api.example.com")
    scope.register_async_resolver("api_client", lambda: create_async_client("https://api.example.com"))

    @inject
    async def async_function_with_async_dep(client: MockAsyncApiClient = Inject["api_client"]) -> str:
        return f"Using client: {client.base_url}"

    async def run_test():
        async with scope:
            with pytest.raises(AsyncDependencyError) as exc_info:
                await async_function_with_async_dep()

            error = exc_info.value
            assert error.function_name == "async_function_with_async_dep"
            assert error.parameter_name == "client"
            assert error.dependency_key == "api_client"
            assert "Cannot use @inject with async dependency" in str(error)
            assert "Use @ainject instead" in str(error)

    asyncio.run(run_test())


def test_inject_with_mixed_dependencies_fails_on_async_ones():
    """Test that @inject fails when mixing sync and async dependencies (fails on async)."""
    scope = DependencyScope()
    scope.register_value("config", {"debug": True})  # Sync dependency
    scope.register_async_resolver("api_client", lambda: create_async_client("https://api.example.com"))  # Async

    @inject
    def mixed_function(config: dict = Inject["config"], client: MockAsyncApiClient = Inject["api_client"]) -> str:
        return f"Config: {config}, Client: {client.base_url}"

    with scope:
        with pytest.raises(AsyncDependencyError) as exc_info:
            mixed_function()

        error = exc_info.value
        assert error.function_name == "mixed_function"
        assert error.parameter_name == "client"
        assert error.dependency_key == "api_client"


def test_inject_with_keyword_only_async_dependency_raises_error():
    """Test that @inject raises AsyncDependencyError for keyword-only parameters."""
    scope = DependencyScope()
    scope.register_async_resolver("api_client", lambda: create_async_client("https://api.example.com"))

    @inject
    def function_with_kwonly_async_dep(*, client: MockAsyncApiClient = Inject["api_client"]) -> str:
        return f"Client: {client.base_url}"

    with scope:
        with pytest.raises(AsyncDependencyError) as exc_info:
            function_with_kwonly_async_dep()

        error = exc_info.value
        assert error.function_name == "function_with_kwonly_async_dep"
        assert error.parameter_name == "client"
        assert error.dependency_key == "api_client"


def test_inject_with_class_methods_and_async_deps():
    """Test that @inject raises AsyncDependencyError for class methods."""
    scope = DependencyScope()
    scope.register_async_resolver("api_client", lambda: create_async_client("https://api.example.com"))

    class TestClass:
        @inject
        def instance_method(self, client: MockAsyncApiClient = Inject["api_client"]) -> str:
            return f"Instance method with client: {client.base_url}"

        @classmethod
        @inject
        def class_method(cls, client: MockAsyncApiClient = Inject["api_client"]) -> str:
            return f"Class method with client: {client.base_url}"

        @staticmethod
        @inject
        def static_method(client: MockAsyncApiClient = Inject["api_client"]) -> str:
            return f"Static method with client: {client.base_url}"

    with scope:
        obj = TestClass()

        # Test instance method
        with pytest.raises(AsyncDependencyError) as exc_info:
            obj.instance_method()
        assert exc_info.value.function_name == "instance_method"

        # Test class method
        with pytest.raises(AsyncDependencyError) as exc_info:
            TestClass.class_method()
        assert exc_info.value.function_name == "class_method"

        # Test static method
        with pytest.raises(AsyncDependencyError) as exc_info:
            TestClass.static_method()
        assert exc_info.value.function_name == "static_method"


def test_ainject_works_with_same_async_dependencies():
    """Test that @ainject works correctly with the same async dependencies that @inject rejects."""
    scope = DependencyScope()
    scope.register_value("base_url", "https://api.example.com")
    scope.register_async_resolver("api_client", lambda: create_async_client("https://api.example.com"))

    @ainject
    async def async_function_works(client: MockAsyncApiClient = Inject["api_client"]) -> str:
        # With @ainject, client is pre-resolved - no Task object!
        assert isinstance(client, MockAsyncApiClient)
        return f"Using client: {client.base_url}"

    async def run_test():
        async with scope:
            result = await async_function_works()
            assert result == "Using client: https://api.example.com"

    asyncio.run(run_test())


def test_inject_works_fine_with_sync_dependencies():
    """Test that @inject continues to work normally with sync dependencies."""
    scope = DependencyScope()
    scope.register_value("config", {"debug": True})
    scope.register_resolver("service", lambda: "TestService")

    @inject
    def sync_function(config: dict = Inject["config"], service: str = Inject["service"]) -> str:
        return f"Config: {config}, Service: {service}"

    with scope:
        result = sync_function()
        assert result == "Config: {'debug': True}, Service: TestService"


def test_error_message_includes_module_name():
    """Test that AsyncDependencyError includes module name in error message."""
    scope = DependencyScope()
    scope.register_async_resolver("api_client", lambda: create_async_client("https://api.example.com"))

    @inject
    def test_function(client: MockAsyncApiClient = Inject["api_client"]) -> str:
        return str(client)

    with scope:
        with pytest.raises(AsyncDependencyError) as exc_info:
            test_function()

        error_msg = str(exc_info.value)
        assert "test_function" in error_msg
        assert "tests.test_async_dependency_error" in error_msg  # Module name
        assert "api_client" in error_msg
        assert "client" in error_msg


def test_explicit_scopes_also_trigger_error():
    """Test that async dependency error occurs even with explicit scopes."""
    explicit_scope = DependencyScope()
    explicit_scope.register_async_resolver("api_client", lambda: create_async_client("https://api.example.com"))

    @inject(scopes=[explicit_scope])
    def function_with_explicit_scope(client: MockAsyncApiClient = Inject["api_client"]) -> str:
        return str(client)

    # Should work without active scope context since we use explicit scope
    with pytest.raises(AsyncDependencyError) as exc_info:
        function_with_explicit_scope()

    error = exc_info.value
    assert error.function_name == "function_with_explicit_scope"
    assert error.dependency_key == "api_client"


def test_direct_scope_access_still_works():
    """Test that direct scope access (not through @inject) still works with async resolvers."""
    scope = DependencyScope()
    scope.register_async_resolver("api_client", lambda: create_async_client("https://api.example.com"))

    async def run_test():
        async with scope:
            # Direct access should still work (returns Task)
            result = scope["api_client"]
            assert hasattr(result, "__await__")  # Should be a Task
            resolved_client = await result
            assert isinstance(resolved_client, MockAsyncApiClient)
            assert resolved_client.base_url == "https://api.example.com"

    asyncio.run(run_test())


def test_async_dependency_error_attributes():
    """Test that AsyncDependencyError has all expected attributes."""
    scope = DependencyScope()
    scope.register_async_resolver("test_key", lambda: create_async_client("https://test.com"))

    @inject
    def test_func(client: MockAsyncApiClient = Inject["test_key"]) -> str:
        return str(client)

    with scope:
        with pytest.raises(AsyncDependencyError) as exc_info:
            test_func()

        error = exc_info.value
        assert error.function_name == "test_func"
        assert error.parameter_name == "client"
        assert error.dependency_key == "test_key"
        assert error.module_name == "tests.test_async_dependency_error"

        # Check that it's properly a subclass of InjectionError
        from injectipy import InjectionError

        assert isinstance(error, InjectionError)
