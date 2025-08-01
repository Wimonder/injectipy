"""Advanced usage patterns for Injectipy dependency injection.

This module demonstrates more sophisticated patterns and use cases
for dependency injection with scope-based management in complex applications.
"""

from typing import Any, Protocol

from injectipy import DependencyScope, Inject, inject

# === Example 1: Protocol-based Dependency Injection ===


class EmailServiceProtocol(Protocol):
    """Protocol for email services."""

    def send_email(self, to: str, subject: str, body: str) -> bool:
        ...


class SMTPEmailService:
    """SMTP implementation of email service."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def send_email(self, to: str, subject: str, body: str) -> bool:
        print(f"Sending email via SMTP ({self.host}:{self.port})")
        print(f"To: {to}, Subject: {subject}")
        return True


class MockEmailService:
    """Mock implementation for testing."""

    def send_email(self, to: str, subject: str, body: str) -> bool:
        print(f"MOCK: Email to {to} with subject '{subject}'")
        return True


def setup_email_services(scope: DependencyScope):
    """Setup email service dependencies."""
    scope.register_value("smtp_host", "smtp.example.com")
    scope.register_value("smtp_port", 587)

    def create_smtp_service(host: str = Inject["smtp_host"], port: int = Inject["smtp_port"]) -> EmailServiceProtocol:
        return SMTPEmailService(host, port)

    scope.register_resolver(EmailServiceProtocol, create_smtp_service, evaluate_once=True)


class NotificationService:
    """Service that depends on email service."""

    @inject
    def __init__(self, email_service: EmailServiceProtocol = Inject[EmailServiceProtocol]):
        self.email_service = email_service

    def send_welcome_email(self, user_email: str):
        return self.email_service.send_email(to=user_email, subject="Welcome!", body="Welcome to our application!")


# === Example 2: Configuration-based Factory Pattern ===


class DatabaseConfig:
    """Database configuration class."""

    def __init__(self, host: str, port: int, database: str, pool_size: int = 10):
        self.host = host
        self.port = port
        self.database = database
        self.pool_size = pool_size

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.host}:{self.port}/{self.database}"


class DatabaseConnection:
    """Database connection class."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        print(f"Connected to {config.connection_string} (pool_size={config.pool_size})")

    def execute(self, query: str) -> list[dict[str, Any]]:
        return [{"result": f"Executed: {query}"}]


def setup_database(scope: DependencyScope):
    """Setup database-related dependencies."""
    db_config = DatabaseConfig(host="localhost", port=5432, database="myapp_prod", pool_size=20)
    scope.register_value("db_config", db_config)

    def create_db_connection(config: DatabaseConfig = Inject["db_config"]) -> DatabaseConnection:
        return DatabaseConnection(config)

    scope.register_resolver("database", create_db_connection, evaluate_once=True)


class UserRepository:
    """Repository for user data access."""

    @inject
    def __init__(self, db: DatabaseConnection = Inject["database"]):
        self.db = db

    def find_user(self, user_id: int) -> dict[str, Any]:
        results = self.db.execute(f"SELECT * FROM users WHERE id = {user_id}")  # nosec B608
        return results[0] if results else {}


# === Example 3: Layered Architecture with DI ===


class CacheServiceProtocol(Protocol):
    """Protocol for cache services."""

    def get(self, key: str) -> Any:
        ...

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        ...


class RedisCache:
    """Redis cache implementation."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        print(f"Connected to Redis at {host}:{port}")

    def get(self, key: str) -> Any:
        print(f"Redis GET: {key}")
        return f"cached_value_for_{key}"

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        print(f"Redis SET: {key} = {value} (TTL: {ttl}s)")
        return True


def setup_cache(scope: DependencyScope):
    """Setup cache dependencies."""
    scope.register_value("redis_host", "localhost")
    scope.register_value("redis_port", 6379)

    def create_redis_cache(host: str = Inject["redis_host"], port: int = Inject["redis_port"]) -> CacheServiceProtocol:
        return RedisCache(host, port)

    scope.register_resolver(CacheServiceProtocol, create_redis_cache, evaluate_once=True)


class UserService:
    """Business logic service with multiple dependencies."""

    @inject
    def __init__(
        self,
        user_repo: UserRepository = Inject[UserRepository],
        cache: CacheServiceProtocol = Inject[CacheServiceProtocol],
        notification: NotificationService = Inject[NotificationService],
    ):
        self.user_repo = user_repo
        self.cache = cache
        self.notification = notification

    def get_user_with_cache(self, user_id: int) -> dict[str, Any]:
        cache_key = f"user_{user_id}"
        cached_user = self.cache.get(cache_key)

        if cached_user:
            return {"source": "cache", "data": cached_user}

        user = self.user_repo.find_user(user_id)

        self.cache.set(cache_key, user, ttl=1800)

        return {"source": "database", "data": user}

    def create_user(self, email: str) -> dict[str, Any]:
        user = {"email": email, "id": 123}

        self.notification.send_welcome_email(email)

        return user


# === Example 4: Factory Dependencies ===


class LoggerFactory:
    """Factory for creating different types of loggers."""

    @inject
    def __init__(self, log_level: str = Inject["log_level"]):
        self.log_level = log_level

    def create_logger(self, name: str) -> "Logger":
        return Logger(name, self.log_level)


class Logger:
    """Simple logger implementation."""

    def __init__(self, name: str, level: str = "INFO"):
        self.name = name
        self.level = level

    def info(self, message: str):
        print(f"[{self.level}] {self.name}: {message}")


def setup_logging(scope: DependencyScope):
    """Setup logging dependencies."""
    scope.register_value("log_level", "DEBUG")
    scope.register_resolver(LoggerFactory, LoggerFactory, evaluate_once=True)


class OrderService:
    """Service that creates its own logger via factory."""

    @inject
    def __init__(self, logger_factory: LoggerFactory = Inject[LoggerFactory]):
        self.logger = logger_factory.create_logger("OrderService")

    def process_order(self, order_id: int):
        self.logger.info(f"Processing order {order_id}")
        return f"Order {order_id} processed"


def main():
    """Demonstrate advanced patterns."""
    print("Advanced Injectipy Patterns")
    print("=" * 50)

    app_scope = DependencyScope()

    setup_email_services(app_scope)
    setup_database(app_scope)
    setup_cache(app_scope)
    setup_logging(app_scope)

    app_scope.register_resolver(UserRepository, UserRepository)
    app_scope.register_resolver(NotificationService, NotificationService)
    app_scope.register_resolver(UserService, UserService)
    app_scope.register_resolver(OrderService, OrderService)

    with app_scope:
        print("\n1. Protocol-based Email Service:")
        notification_service = NotificationService()
        notification_service.send_welcome_email("user@example.com")

        print("\n2. Layered Architecture:")
        user_service = UserService()
        user_result = user_service.get_user_with_cache(123)
        print(f"User result: {user_result}")

        print("\n3. User Creation with Notification:")
        new_user = user_service.create_user("newuser@example.com")
        print(f"Created user: {new_user}")

        print("\n4. Factory Pattern:")
        order_service = OrderService()
        order_result = order_service.process_order(456)
        print(f"Order result: {order_result}")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
