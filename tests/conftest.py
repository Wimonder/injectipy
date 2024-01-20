"""Shared test configuration and fixtures for injectipy tests."""

import pytest

from injectipy import DependencyScope, clear_scope_stack


@pytest.fixture
def clean_scope():
    """Provide a completely clean DependencyScope instance."""
    return DependencyScope()


@pytest.fixture
def basic_scope():
    """Provide a scope with basic test dependencies."""
    scope = DependencyScope()
    scope.register_value("service", "injected_service")
    scope.register_value("config", {"debug": True, "env": "test"})
    return scope


@pytest.fixture
def multi_service_scope():
    """Provide a scope with multiple services for complex tests."""
    scope = DependencyScope()
    scope.register_value("service1", "injected_service1")
    scope.register_value("service2", "injected_service2")
    scope.register_value("dep1", "injected_dep1")
    scope.register_value("dep2", "injected_dep2")
    scope.register_value("config", {"setting": "value"})
    return scope


@pytest.fixture(autouse=True)
def ensure_clean_state():
    """Ensure clean state before each test by clearing the scope stack."""
    clear_scope_stack()
    yield
    # Cleanup after test
    clear_scope_stack()
