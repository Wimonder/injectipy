"""Testing patterns and best practices with Injectipy.

This module demonstrates how to effectively test code that uses
scope-based dependency injection, including mocking and test isolation.
"""

from typing import Protocol

import pytest

from injectipy import DependencyScope, Inject, inject

# === Production Code ===


class EmailServiceProtocol(Protocol):
    """Protocol for email services."""

    def send_email(self, to: str, subject: str, body: str) -> bool:
        ...


class DatabaseProtocol(Protocol):
    """Protocol for database access."""

    def query(self, sql: str) -> list[dict]:
        ...


class ProductionEmailService:
    """Production email service."""

    def send_email(self, to: str, subject: str, body: str) -> bool:
        print(f"Sending real email to {to}")
        return True


class ProductionDatabase:
    """Production database implementation."""

    def query(self, sql: str) -> list[dict]:
        print(f"Executing real query: {sql}")
        return [{"id": 1, "name": "John"}]


class UserService:
    """Business service with dependencies."""

    @inject
    def __init__(
        self,
        email_service: EmailServiceProtocol = Inject[EmailServiceProtocol],
        database: DatabaseProtocol = Inject[DatabaseProtocol],
    ):
        self.email_service = email_service
        self.database = database

    def register_user(self, email: str, name: str) -> dict:
        user_data = {"email": email, "name": name}
        self.database.query(f"INSERT INTO users (email, name) VALUES ('{email}', '{name}')")  # nosec B608

        success = self.email_service.send_email(
            to=email, subject="Welcome!", body=f"Hello {name}, welcome to our service!"
        )

        return {"user": user_data, "email_sent": success}

    def get_user_count(self) -> int:
        results = self.database.query("SELECT COUNT(*) as count FROM users")
        return results[0]["count"] if results else 0


# === Testing with Isolated Store ===


class TestUserServiceWithIsolatedScope:
    """Test class demonstrating isolated scope usage."""

    def setup_method(self):
        """Create a fresh scope for each test."""
        self.test_scope = DependencyScope()

        # Setup mock dependencies
        self.mock_email_service = MockEmailService()
        self.mock_database = MockDatabase()

        self.test_scope.register_value(EmailServiceProtocol, self.mock_email_service)
        self.test_scope.register_value(DatabaseProtocol, self.mock_database)

    def create_user_service(self) -> UserService:
        """Create UserService with test dependencies within scope context."""
        # This should be called within a scope context
        return UserService()

    def test_register_user_success(self):
        """Test successful user registration."""
        with self.test_scope:
            service = self.create_user_service()

            result = service.register_user("test@example.com", "Test User")

            assert result["user"]["email"] == "test@example.com"
            assert result["user"]["name"] == "Test User"
            assert result["email_sent"] is True

            # Verify database was called
            assert len(self.mock_database.executed_queries) == 1
            assert "INSERT INTO users" in self.mock_database.executed_queries[0]

            # Verify email was sent
            assert len(self.mock_email_service.sent_emails) == 1
            assert self.mock_email_service.sent_emails[0]["to"] == "test@example.com"

    def test_get_user_count(self):
        """Test getting user count."""
        # Setup mock to return specific count
        self.mock_database.query_results = [{"count": 42}]

        with self.test_scope:
            service = self.create_user_service()
            count = service.get_user_count()

            assert count == 42
            assert "SELECT COUNT(*)" in self.mock_database.executed_queries[0]


# === Testing with Scoped Isolation (Recommended Pattern) ===


class TestUserServiceWithScopedIsolation:
    """Test class using scoped isolation pattern."""

    def setup_method(self):
        """Create isolated scope for each test."""
        self.test_scope = DependencyScope()

        self.mock_email_service = MockEmailService()
        self.mock_database = MockDatabase()

        # Register test dependencies in isolated scope
        self.test_scope.register_value(EmailServiceProtocol, self.mock_email_service)
        self.test_scope.register_value(DatabaseProtocol, self.mock_database)

    def create_user_service(self) -> UserService:
        """Create UserService with test dependencies."""
        # Create service within scope context
        return UserService()

    def test_email_failure_handling(self):
        """Test handling of email service failure."""
        # Configure mock to fail
        self.mock_email_service.should_fail = True

        with self.test_scope:
            service = self.create_user_service()
            result = service.register_user("test@example.com", "Test User")

            assert result["email_sent"] is False
            assert len(self.mock_email_service.sent_emails) == 0


# === Mock Implementations ===


class MockEmailService:
    """Mock email service for testing."""

    def __init__(self):
        self.sent_emails = []
        self.should_fail = False

    def send_email(self, to: str, subject: str, body: str) -> bool:
        if self.should_fail:
            return False

        self.sent_emails.append({"to": to, "subject": subject, "body": body})
        return True


class MockDatabase:
    """Mock database for testing."""

    def __init__(self):
        self.executed_queries = []
        self.query_results = []

    def query(self, sql: str) -> list[dict]:
        self.executed_queries.append(sql)

        if self.query_results:
            return self.query_results

        # Default responses based on query type
        if "COUNT(*)" in sql:
            return [{"count": 5}]
        elif "INSERT" in sql:
            return [{"id": 1}]
        else:
            return [{"id": 1, "name": "Mock User"}]


# === Integration Test Example ===


def test_integration_with_real_dependencies():
    """Example of integration test with real dependencies."""
    # Create isolated scope for integration test
    integration_scope = DependencyScope()

    # Register real dependencies
    integration_scope.register_value(EmailServiceProtocol, ProductionEmailService())
    integration_scope.register_value(DatabaseProtocol, ProductionDatabase())

    with integration_scope:
        # Create service with real dependencies
        service = UserService()

        # This would interact with real services
        print("Running integration test...")
        result = service.register_user("integration@example.com", "Integration Test")
        print(f"Integration result: {result}")


# === Fixture-based Testing Pattern ===


@pytest.fixture
def mock_email_service():
    """Pytest fixture for mock email service."""
    return MockEmailService()


@pytest.fixture
def mock_database():
    """Pytest fixture for mock database."""
    return MockDatabase()


@pytest.fixture
def test_scope(mock_email_service, mock_database):
    """Pytest fixture for test scope with mocks."""
    scope = DependencyScope()
    scope.register_value(EmailServiceProtocol, mock_email_service)
    scope.register_value(DatabaseProtocol, mock_database)
    return scope


def test_with_fixtures(test_scope, mock_email_service, mock_database):
    """Test using pytest fixtures."""
    with test_scope:
        service = UserService()

        result = service.register_user("fixture@example.com", "Fixture Test")

        assert result["email_sent"] is True
        assert len(mock_email_service.sent_emails) == 1
        assert len(mock_database.executed_queries) == 1


def main():
    """Demonstrate testing patterns."""
    print("Testing Patterns with Injectipy")
    print("=" * 40)

    print("\n1. Unit Test with Isolated Scope:")
    test_class = TestUserServiceWithIsolatedScope()
    test_class.setup_method()
    test_class.test_register_user_success()
    print("✓ Unit test passed")

    print("\n2. Test with Email Failure:")
    test_class2 = TestUserServiceWithScopedIsolation()
    test_class2.setup_method()
    test_class2.test_email_failure_handling()
    print("✓ Email failure test passed")

    print("\n3. Integration Test:")
    test_integration_with_real_dependencies()
    print("✓ Integration test completed")

    print("\n" + "=" * 40)
    print("Key Testing Principles:")
    print("- Use isolated scopes for unit tests")
    print("- Mock external dependencies")
    print("- Test both success and failure cases")
    print("- Use fixtures for reusable test setup")
    print("- Leverage scope context managers for clean isolation")


if __name__ == "__main__":
    main()
