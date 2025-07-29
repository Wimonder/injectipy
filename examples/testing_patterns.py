"""Testing patterns and best practices with Injectipy.

This module demonstrates how to effectively test code that uses
dependency injection, including mocking and test isolation.
"""

from typing import Protocol

import pytest

from injectipy import Inject, InjectipyStore, inject

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
        # Save user to database
        user_data = {"email": email, "name": name}
        self.database.query(f"INSERT INTO users (email, name) VALUES ('{email}', '{name}')")  # nosec B608

        # Send welcome email
        success = self.email_service.send_email(
            to=email, subject="Welcome!", body=f"Hello {name}, welcome to our service!"
        )

        return {"user": user_data, "email_sent": success}

    def get_user_count(self) -> int:
        results = self.database.query("SELECT COUNT(*) as count FROM users")
        return results[0]["count"] if results else 0


# === Testing with Isolated Store ===


class TestUserServiceWithIsolatedStore:
    """Test class demonstrating isolated store usage."""

    def setup_method(self):
        """Create a fresh store for each test."""
        self.test_store = InjectipyStore()

        # Setup mock dependencies
        self.mock_email_service = MockEmailService()
        self.mock_database = MockDatabase()

        self.test_store.register_value(EmailServiceProtocol, self.mock_email_service)
        self.test_store.register_value(DatabaseProtocol, self.mock_database)

    def create_user_service(self) -> UserService:
        """Create UserService with test dependencies."""
        # Manually inject dependencies from test store
        return UserService(
            email_service=self.test_store[EmailServiceProtocol], database=self.test_store[DatabaseProtocol]
        )

    def test_register_user_success(self):
        """Test successful user registration."""
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

        service = self.create_user_service()
        count = service.get_user_count()

        assert count == 42
        assert "SELECT COUNT(*)" in self.mock_database.executed_queries[0]


# === Testing with Global Store Reset (Production Pattern) ===


class TestUserServiceWithGlobalStore:
    """Test class using global store with reset."""

    def setup_method(self):
        """Reset global store and setup test dependencies."""
        from injectipy import injectipy_store

        # Reset store for clean slate (this would use _reset_for_testing() in real tests)
        # For this example, we'll register with unique keys

        self.mock_email_service = MockEmailService()
        self.mock_database = MockDatabase()

        # Use unique keys for each test to avoid conflicts
        import time

        self.test_id = str(int(time.time()))

        # Register test dependencies with unique keys
        injectipy_store.register_value(f"test_email_{self.test_id}", self.mock_email_service)
        injectipy_store.register_value(f"test_db_{self.test_id}", self.mock_database)

    def create_user_service(self) -> UserService:
        """Create UserService with test dependencies."""
        from injectipy import injectipy_store

        return UserService(
            email_service=injectipy_store[f"test_email_{self.test_id}"],
            database=injectipy_store[f"test_db_{self.test_id}"],
        )

    def test_email_failure_handling(self):
        """Test handling of email service failure."""
        # Configure mock to fail
        self.mock_email_service.should_fail = True

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
    # Create isolated store for integration test
    integration_store = InjectipyStore()

    # Register real dependencies
    integration_store.register_value(EmailServiceProtocol, ProductionEmailService())
    integration_store.register_value(DatabaseProtocol, ProductionDatabase())

    # Create service with real dependencies
    service = UserService(
        email_service=integration_store[EmailServiceProtocol], database=integration_store[DatabaseProtocol]
    )

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
def test_store(mock_email_service, mock_database):
    """Pytest fixture for test store with mocks."""
    store = InjectipyStore()
    store.register_value(EmailServiceProtocol, mock_email_service)
    store.register_value(DatabaseProtocol, mock_database)
    return store


def test_with_fixtures(test_store, mock_email_service, mock_database):
    """Test using pytest fixtures."""
    service = UserService(email_service=test_store[EmailServiceProtocol], database=test_store[DatabaseProtocol])

    result = service.register_user("fixture@example.com", "Fixture Test")

    assert result["email_sent"] is True
    assert len(mock_email_service.sent_emails) == 1
    assert len(mock_database.executed_queries) == 1


def main():
    """Demonstrate testing patterns."""
    print("Testing Patterns with Injectipy")
    print("=" * 40)

    print("\n1. Unit Test with Isolated Store:")
    test_class = TestUserServiceWithIsolatedStore()
    test_class.setup_method()
    test_class.test_register_user_success()
    print("✓ Unit test passed")

    print("\n2. Test with Email Failure:")
    test_class2 = TestUserServiceWithGlobalStore()
    test_class2.setup_method()
    test_class2.test_email_failure_handling()
    print("✓ Email failure test passed")

    print("\n3. Integration Test:")
    test_integration_with_real_dependencies()
    print("✓ Integration test completed")

    print("\n" + "=" * 40)
    print("Key Testing Principles:")
    print("- Use isolated stores for unit tests")
    print("- Mock external dependencies")
    print("- Test both success and failure cases")
    print("- Use fixtures for reusable test setup")


if __name__ == "__main__":
    main()
