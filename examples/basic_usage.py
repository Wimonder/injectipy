"""Basic usage examples for Injectipy dependency injection.

This module demonstrates the fundamental patterns for using Injectipy
with scope-based dependency management.
"""

from injectipy import DependencyScope, Inject, inject


def example_1_simple_values():
    """Example 1: Register and inject simple values."""
    print("=== Example 1: Simple Values ===")

    scope = DependencyScope()
    scope.register_value("app_name", "MyApplication")
    scope.register_value("version", "1.0.0")
    scope.register_value("debug", True)

    @inject
    def show_app_info(name: str = Inject["app_name"], version: str = Inject["version"], debug: bool = Inject["debug"]):
        status = "DEBUG" if debug else "PRODUCTION"
        return f"{name} v{version} ({status})"

    with scope:
        result = show_app_info()
        print(f"App Info: {result}")

        custom_result = show_app_info(name="CustomApp")
        print(f"Custom App Info: {custom_result}")


def example_2_factory_functions():
    """Example 2: Using factory functions as dependencies."""
    print("\n=== Example 2: Factory Functions ===")

    scope = DependencyScope()
    scope.register_value("db_host", "localhost")
    scope.register_value("db_port", 5432)
    scope.register_value("db_name", "myapp")

    def create_database_url(
        host: str = Inject["db_host"], port: int = Inject["db_port"], database: str = Inject["db_name"]
    ):
        return f"postgresql://{host}:{port}/{database}"

    scope.register_resolver("database_url", create_database_url)

    @inject
    def connect_to_database(url: str = Inject["database_url"]):
        return f"Connected to: {url}"

    with scope:
        result = connect_to_database()
        print(f"Database Connection: {result}")


def example_3_singletons():
    """Example 3: Creating singleton dependencies with evaluate_once."""
    print("\n=== Example 3: Singleton Pattern ===")

    scope = DependencyScope()

    class ExpensiveResource:
        """Simulate an expensive resource to create."""

        _instance_count = 0

        def __init__(self):
            ExpensiveResource._instance_count += 1
            self.instance_id = ExpensiveResource._instance_count
            print(f"  Creating ExpensiveResource instance #{self.instance_id}")

        def do_work(self):
            return f"Working with instance #{self.instance_id}"

    scope.register_resolver("expensive_resource", ExpensiveResource, evaluate_once=True)

    @inject
    def worker_1(resource: ExpensiveResource = Inject["expensive_resource"]):
        return f"Worker 1: {resource.do_work()}"

    @inject
    def worker_2(resource: ExpensiveResource = Inject["expensive_resource"]):
        return f"Worker 2: {resource.do_work()}"

    with scope:
        print("Calling worker_1 (should create instance):")
        result1 = worker_1()
        print(result1)

        print("Calling worker_2 (should reuse instance):")
        result2 = worker_2()
        print(result2)

        print(f"Total instances created: {ExpensiveResource._instance_count}")


def example_4_class_injection():
    """Example 4: Dependency injection in class constructors."""
    print("\n=== Example 4: Class Constructor Injection ===")

    scope = DependencyScope()
    scope.register_value("user_service_logger", "FileLogger")
    scope.register_value("user_service_cache", "RedisCache")

    class UserService:
        """Service class with injected dependencies."""

        @inject
        def __init__(self, logger: str = Inject["user_service_logger"], cache: str = Inject["user_service_cache"]):
            self.logger = logger
            self.cache = cache

        def get_user(self, user_id: int):
            # Simulate logging and caching
            return f"User {user_id} (logged by {self.logger}, cached in {self.cache})"

    with scope:
        service = UserService()
        result = service.get_user(123)
        print(f"Service Result: {result}")

        custom_service = UserService(logger="CustomLogger")
        custom_result = custom_service.get_user(456)
        print(f"Custom Service Result: {custom_result}")


def example_5_type_based_keys():
    """Example 5: Using types as dependency keys."""
    print("\n=== Example 5: Type-based Keys ===")

    from typing import Protocol

    scope = DependencyScope()

    class DatabaseProtocol(Protocol):
        """Protocol defining database interface."""

        def query(self, sql: str) -> list:
            ...

    class PostgreSQLDatabase:
        """Concrete PostgreSQL implementation."""

        def query(self, sql: str) -> list:
            return [f"PostgreSQL result for: {sql}"]

    class AppLogger:
        """Simple logger class."""

        def log(self, message: str):
            return f"LOG: {message}"

    scope.register_value(DatabaseProtocol, PostgreSQLDatabase())
    scope.register_value(AppLogger, AppLogger())

    @inject
    def get_users(db: DatabaseProtocol = Inject[DatabaseProtocol], logger: AppLogger = Inject[AppLogger]) -> list:
        logger.log("Fetching users from database")
        return db.query("SELECT * FROM users")

    with scope:
        result = get_users()
        print(f"Query Result: {result}")


def example_6_nested_dependencies():
    """Example 6: Nested dependency resolution."""
    print("\n=== Example 6: Nested Dependencies ===")

    scope = DependencyScope()
    scope.register_value("api_endpoint", "https://api.example.com")
    scope.register_value("timeout", 30)

    def create_http_client(endpoint: str = Inject["api_endpoint"], timeout: int = Inject["timeout"]):
        return f"HTTPClient(endpoint={endpoint}, timeout={timeout}s)"

    scope.register_resolver("http_client", create_http_client)

    @inject
    def make_api_request(path: str, client: str = Inject["http_client"]):
        return f"Making request to {path} using {client}"

    with scope:
        result = make_api_request("/users")
        print(f"API Request: {result}")


if __name__ == "__main__":
    """Run all examples."""
    print("Injectipy Basic Usage Examples")
    print("=" * 40)

    example_1_simple_values()
    example_2_factory_functions()
    example_3_singletons()
    example_4_class_injection()
    example_5_type_based_keys()
    example_6_nested_dependencies()

    print("\n" + "=" * 40)
    print("All examples completed!")
