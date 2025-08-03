# Injectipy

A dependency injection library for Python that uses explicit scopes instead of global state. Provides type-safe dependency resolution with circular dependency detection.

[![PyPI version](https://badge.fury.io/py/injectipy.svg)](https://badge.fury.io/py/injectipy)
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Type Checked](https://img.shields.io/badge/typed-mypy-blue.svg)](https://mypy.readthedocs.io/)

## Key Features

- **Explicit scopes**: Dependencies managed within context managers, no global state
- **Async/await support**: Clean async dependency injection with `@ainject` decorator
- **Type safety**: Works with mypy and provides runtime type checking
- **Circular dependency detection**: Detects dependency cycles at registration time
- **Thread safety**: Each scope is isolated, safe for concurrent use
- **Lazy evaluation**: Dependencies resolved only when accessed
- **Test isolation**: Each test can use its own scope with different dependencies

## Installation

```bash
pip install injectipy
```

## Quick Start

### Basic Usage

```python
from injectipy import inject, Inject, DependencyScope

# Create a dependency scope
scope = DependencyScope()

# Register a simple value
scope.register_value("database_url", "postgresql://localhost/mydb")

# Register a factory function
def create_database_connection(database_url: str = Inject["database_url"]):
    return f"Connected to {database_url}"

scope.register_resolver("db_connection", create_database_connection)

# Use dependency injection in your functions within a scope context
@inject
def get_user(user_id: int, db_connection: str = Inject["db_connection"]):
    return f"User {user_id} from {db_connection}"

# Use the scope as a context manager
with scope:
    user = get_user(123)
    print(user)  # "User 123 from Connected to postgresql://localhost/mydb"
```

### Async/Await Support with `@ainject`

Injectipy provides strict separation between sync and async dependency injection:

- **`@inject`**: Only works with sync dependencies. **Rejects async dependencies with clear error messages.**
- **`@ainject`**: Designed for async functions, automatically awaits async dependencies before function execution.

The `@ainject` decorator provides clean async dependency injection by automatically awaiting async dependencies:

```python
import asyncio
from injectipy import ainject, Inject, DependencyScope

# Create a scope with async dependencies
scope = DependencyScope()
scope.register_value("base_url", "https://api.example.com")
scope.register_value("api_key", "secret-key")

# Register an async factory
async def create_api_client(base_url: str = Inject["base_url"], api_key: str = Inject["api_key"]):
    await asyncio.sleep(0.1)  # Simulate async initialization
    return {"url": base_url, "key": api_key}

scope.register_async_resolver("api_client", create_api_client)

# ❌ WRONG: @inject rejects async dependencies
@inject
async def wrong_way(endpoint: str, client = Inject["api_client"]):
    # This will raise AsyncDependencyError!
    return await client.fetch(endpoint)

# ✅ CORRECT: Use @ainject for async dependencies
@ainject
async def correct_way(endpoint: str, client = Inject["api_client"]):
    # @ainject pre-awaits async dependencies - client is ready to use!
    return await client.fetch(endpoint)

async def main():
    async with scope:
        try:
            await wrong_way("/users")  # Raises AsyncDependencyError
        except Exception as e:
            print(f"Error: {e}")
            print("Use @ainject instead!")

        # This works correctly
        data = await correct_way("/users")
        print(data)

asyncio.run(main())
```

**Key Benefits:**
- **Clear separation**: No confusion about which decorator to use
- **Better error messages**: `@inject` guides you to use `@ainject` when needed
- **Type safety**: Eliminates manual `hasattr(..., '__await__')` checks
- **Clean code**: `@ainject` pre-resolves all dependencies before function execution

### Class-based Injection

```python
from injectipy import inject, Inject, DependencyScope

# Create and configure a scope
scope = DependencyScope()
scope.register_value("db_connection", "PostgreSQL://localhost")
scope.register_value("config", "production_config")
scope.register_value("helper", "UtilityHelper")

class UserService:
    @inject
    def __init__(self, db_connection: str = Inject["db_connection"]):
        self.db = db_connection

    def get_user(self, user_id: int):
        return f"User {user_id} from {self.db}"

    @inject
    @classmethod
    def create_service(cls, config: str = Inject["config"]):
        return cls()

    @inject
    @staticmethod
    def utility_function(helper: str = Inject["helper"]):
        return f"Helper: {helper}"

# Use within scope context for dependency injection
with scope:
    service = UserService()
    print(service.get_user(456))
```

### Factory Functions with Dependencies

```python
from injectipy import inject, Inject, DependencyScope

# Create and configure a scope
scope = DependencyScope()

# Register configuration
scope.register_value("api_key", "secret123")
scope.register_value("base_url", "https://api.example.com")

# Factory function that depends on other registered dependencies
def create_api_client(
    api_key: str = Inject["api_key"],
    base_url: str = Inject["base_url"]
):
    return f"APIClient(key={api_key}, url={base_url})"

# Register the factory
scope.register_resolver("api_client", create_api_client)

# Use in your code within scope context
@inject
def fetch_data(client = Inject["api_client"]):
    return f"Fetching data with {client}"

with scope:
    print(fetch_data())
```

### Singleton Pattern with `evaluate_once`

```python
from injectipy import DependencyScope
import time

def expensive_resource():
    print("Creating expensive resource...")
    time.sleep(1)  # Simulate expensive operation
    return "ExpensiveResource"

# Create scope and register with evaluate_once=True for singleton behavior
scope = DependencyScope()
scope.register_resolver(
    "expensive_resource",
    expensive_resource,
    evaluate_once=True
)

with scope:
    # First access creates the resource
    resource1 = scope["expensive_resource"]  # Prints "Creating..."
    resource2 = scope["expensive_resource"]  # No print, reuses cached

    assert resource1 is resource2  # Same instance
```

## Advanced Usage

### Keyword-Only Parameters

The `@inject` decorator supports keyword-only parameters:

```python
from injectipy import inject, Inject, DependencyScope

# Create scope and register dependencies
scope = DependencyScope()
scope.register_value("database", "ProductionDB")
scope.register_value("cache", "RedisCache")

@inject
def process_data(data: str, *, db=Inject["database"], cache=Inject["cache"], debug=False):
    return f"Processing {data} with {db}, {cache}, debug={debug}"

with scope:
    # Keyword-only parameters work seamlessly
    result = process_data("user_data")
    print(result)  # "Processing user_data with ProductionDB, RedisCache, debug=False"

    # Override specific parameters
    result = process_data("user_data", cache="MemoryCache", debug=True)
    print(result)  # "Processing user_data with ProductionDB, MemoryCache, debug=True"
```

### Decorator Compatibility

The `@inject` decorator works with other Python decorators. Order matters:

```python
from injectipy import inject, Inject, DependencyScope

# Create scope and register dependencies
scope = DependencyScope()
scope.register_value("logger", "ProductionLogger")

class APIService:
    # ✅ Recommended order: @inject comes after @classmethod/@staticmethod
    @inject
    @classmethod
    def create_from_config(cls, logger=Inject["logger"]):
        return cls(logger)

    @inject
    @staticmethod
    def validate_data(data, logger=Inject["logger"]):
        print(f"Validating with {logger}")
        return True

# Works with other decorators too
def timer_decorator(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return f"timed({result})"
    return wrapper

@timer_decorator
@inject
def process_data(data, logger=Inject["logger"]):
    return f"Processed {data} with {logger}"

with scope:
    result = process_data("user_data")
    print(result)  # "timed(Processed user_data with ProductionLogger)"
```

**Decorator ordering rules:**
- `@inject` comes after `@classmethod` or `@staticmethod`
- `@inject` comes after other decorators (`@contextmanager`, `@lru_cache`, `@property`)
- Apply `@inject` last (closest to the function definition)

```python
# Correct order
@classmethod
@inject
def create_service(cls, dep=Inject["service"]): ...

@lru_cache(maxsize=128)
@inject
def cached_func(dep=Inject["service"]): ...
```

### Type-Based Registration and Injection

Use types directly as keys for enhanced type safety:

```python
from typing import Protocol
from injectipy import inject, Inject, DependencyScope

class DatabaseProtocol(Protocol):
    def query(self, sql: str) -> list: ...

class PostgreSQLDatabase:
    def query(self, sql: str) -> list:
        return ["result1", "result2"]

class CacheService:
    def get(self, key: str) -> str | None:
        return f"cached_{key}"

class ConfigService:
    def __init__(self, env: str):
        self.env = env

    def get_database_url(self) -> str:
        return f"postgresql://localhost/{self.env}"

# Register dependencies using types as keys
scope = DependencyScope()
scope.register_value(DatabaseProtocol, PostgreSQLDatabase())
scope.register_value(CacheService, CacheService())
scope.register_value(ConfigService, ConfigService("production"))

@inject
def process_user(
    user_id: int,
    db: DatabaseProtocol = Inject[DatabaseProtocol],
    cache: CacheService = Inject[CacheService],
    config: ConfigService = Inject[ConfigService]
) -> str:
    users = db.query("SELECT * FROM users WHERE id = ?")
    cached_data = cache.get(f"user_{user_id}")
    db_url = config.get_database_url()
    return f"User data: {users}, cached: {cached_data}, db: {db_url}"

with scope:
    # Full type safety - mypy knows exact types
    result = process_user(123)
```

### String-Based Registration

You can also use string keys for more flexible scenarios:

```python
from typing import Protocol
from injectipy import inject, Inject, DependencyScope

class DatabaseProtocol(Protocol):
    def query(self, sql: str) -> list: ...

class PostgreSQLDatabase:
    def query(self, sql: str) -> list:
        return ["result1", "result2"]

# Create scope and register with string keys
scope = DependencyScope()
scope.register_value("database", PostgreSQLDatabase())
scope.register_value("app_name", "MyApp")

@inject
def get_users(db: DatabaseProtocol = Inject["database"], app: str = Inject["app_name"]) -> list:
    print(f"Querying from {app}")
    return db.query("SELECT * FROM users")

with scope:
    # mypy will verify types correctly
    users: list = get_users()
```


### Scope Isolation and Nesting

You can create multiple isolated scopes and even nest them:

```python
from injectipy import DependencyScope, inject, Inject

# Create separate scopes for different contexts
production_scope = DependencyScope()
production_scope.register_value("config", {"env": "production"})
production_scope.register_value("db_url", "postgresql://prod-server/db")

test_scope = DependencyScope()
test_scope.register_value("config", {"env": "test"})
test_scope.register_value("db_url", "sqlite:///:memory:")

@inject
def get_environment(config: dict = Inject["config"]):
    return config["env"]

# Use different scopes for different contexts
with production_scope:
    print(get_environment())  # "production"

with test_scope:
    print(get_environment())  # "test"

# Scopes can also be nested - inner scope takes precedence
with production_scope:
    with test_scope:
        print(get_environment())  # "test" (inner scope wins)
```

## Error Handling

The library raises clear error messages for common issues:

```python
from injectipy import inject, ainject, Inject, DependencyScope
from injectipy import (
    DependencyNotFoundError,
    CircularDependencyError,
    DuplicateRegistrationError,
    AsyncDependencyError  # New!
)

# Missing dependency
@inject
def missing_dep(value: str = Inject["nonexistent"]):
    return value

try:
    missing_dep()
except DependencyNotFoundError as e:
    print(e)  # "Dependency 'nonexistent' not found"

# Async dependency with @inject (NEW!)
async def async_service():
    return "AsyncService"

scope = DependencyScope()
scope.register_async_resolver("async_service", async_service)

@inject
def wrong_decorator(service = Inject["async_service"]):
    return service

with scope:
    try:
        wrong_decorator()
    except AsyncDependencyError as e:
        print(e)  # "Cannot use @inject with async dependency 'async_service'. Use @ainject instead."

# Circular dependency (detected at registration)
def service_a(b = Inject["service_b"]):
    return f"A: {b}"

def service_b(a = Inject["service_a"]):
    return f"B: {a}"

scope = DependencyScope()
scope.register_resolver("service_a", service_a)

try:
    scope.register_resolver("service_b", service_b)
except CircularDependencyError as e:
    print(e)  # "Circular dependency detected"

# Duplicate registration
scope = DependencyScope()
scope.register_value("config", "prod")

try:
    scope.register_value("config", "dev")
except DuplicateRegistrationError as e:
    print(e)  # "Key 'config' already registered"
```

## Testing

Use separate scopes for test isolation:

```python
import pytest
from injectipy import DependencyScope, inject, Inject

@pytest.fixture
def test_scope():
    """Provide a clean scope for each test"""
    return DependencyScope()

def test_dependency_injection(test_scope):
    test_scope.register_value("test_value", "hello")

    @inject
    def test_function(value: str = Inject["test_value"]):
        return value

    with test_scope:
        assert test_function() == "hello"

def test_isolation(test_scope):
    # Each test gets a fresh scope, so dependencies are isolated
    test_scope.register_value("isolated_value", "test_specific")

    @inject
    def isolated_function(value: str = Inject["isolated_value"]):
        return value

    with test_scope:
        assert isolated_function() == "test_specific"

def test_scoped_mocking(test_scope):
    # Easy to mock dependencies per test
    test_scope.register_value("database", "MockDatabase")
    test_scope.register_value("cache", "MockCache")

    @inject
    def service_function(db=Inject["database"], cache=Inject["cache"]):
        return f"Using {db} and {cache}"

    with test_scope:
        result = service_function()
        assert result == "Using MockDatabase and MockCache"
```

## Thread Safety

Scopes are thread-safe and can be shared between threads:

```python
import threading
from injectipy import DependencyScope, inject, Inject

# Create a shared scope
shared_scope = DependencyScope()
shared_scope.register_value("shared_resource", "ThreadSafeResource")

@inject
def worker_function(resource: str = Inject["shared_resource"]):
    return f"Worker using {resource}"

def worker():
    with shared_scope:  # Each thread uses the same scope safely
        print(worker_function())

# Safe to use across multiple threads
threads = []
for i in range(10):
    thread = threading.Thread(target=worker)
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()
```

## Async/Await Support

DependencyScope supports both sync and async context managers:

```python
import asyncio
from injectipy import DependencyScope, inject, Inject

scope = DependencyScope()
scope.register_value("api_key", "secret-key")

@inject
async def fetch_data(endpoint: str, api_key: str = Inject["api_key"]) -> dict:
    # Simulate async API call
    await asyncio.sleep(0.1)
    return {"endpoint": endpoint, "authenticated": bool(api_key)}

async def main():
    async with scope:  # Use async context manager
        data = await fetch_data("/users")
        print(data)

asyncio.run(main())
```

### Concurrent Async Tasks

Each task gets proper context isolation:

```python
async def concurrent_example():
    async def task_with_scope(task_id: int):
        task_scope = DependencyScope()
        task_scope.register_value("task_id", task_id)

        async with task_scope:
            @inject
            async def process_task(task_id: int = Inject["task_id"]) -> str:
                await asyncio.sleep(0.1)
                return f"Processed task {task_id}"

            return await process_task()

    # Run multiple tasks concurrently with proper isolation
    results = await asyncio.gather(
        task_with_scope(1),
        task_with_scope(2),
        task_with_scope(3)
    )
    print(results)  # ['Processed task 1', 'Processed task 2', 'Processed task 3']

asyncio.run(concurrent_example())
```

## API Reference

### Core Components

#### `@inject` decorator
Decorates functions/methods to enable automatic dependency injection within active scopes. **Only works with sync dependencies** - rejects async dependencies with `AsyncDependencyError`.

#### `@ainject` decorator
Decorates async functions to enable automatic dependency injection with proper async/await handling. Automatically awaits async dependencies before function execution.

#### `Inject[key]`
Type-safe dependency marker for function parameters.

#### `DependencyScope`
Context manager for managing dependency lifecycles and isolation.

### DependencyScope Methods

#### `register_value(key, value)`
Register a static value as a dependency. Returns self for method chaining.

#### `register_resolver(key, resolver, *, evaluate_once=False)`
Register a sync factory function as a dependency. Returns self for method chaining.
- `evaluate_once=True`: Cache the result after first evaluation (singleton pattern)

#### `register_async_resolver(key, async_resolver, *, evaluate_once=False)`
Register an async factory function as a dependency. Returns self for method chaining.
- `evaluate_once=True`: Cache the result after first evaluation (singleton pattern)
- Use with `@ainject` decorator for clean async dependency injection

#### `[key]` (getitem)
Resolve and return a dependency by key. Only works within active scope context.

#### `contains(key)`
Check if a dependency key is registered in this scope.

#### `is_active()`
Check if this scope is currently active (within a `with` block).

#### Context Manager Protocol
- `__enter__()`: Activate the scope
- `__exit__()`: Deactivate the scope and clean up

## Documentation

Full documentation is available at [wimonder.github.io/injectipy](https://wimonder.github.io/injectipy/).

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and contribution guidelines.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/Wimonder/injectipy.git
cd injectipy

# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run type checking
poetry run mypy injectipy/

# Run linting
poetry run ruff check .
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=injectipy

# Run specific test files
poetry run pytest tests/test_core_inject.py
poetry run pytest tests/test_scope_functionality.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### Version 0.3.0 (2025-01-03)
- **NEW**: `@ainject` decorator for clean async dependency injection
- **NEW**: `AsyncDependencyError` with helpful error messages guiding users to correct decorator
- **BREAKING**: `@inject` now strictly rejects async dependencies (use `@ainject` instead)
- **Enhanced**: Strict separation between sync and async dependency injection
- **Performance**: Optimized async resolver detection with caching
- **Documentation**: Updated README with comprehensive async/await examples

### Version 0.1.0 (2024-01-20)
- **Initial release** of Injectipy dependency injection library
- **Core features**: `@inject` decorator, `Inject[key]` markers, `DependencyScope` context managers
- **Advanced capabilities**: Thread safety, circular dependency detection, lazy evaluation
- **Modern Python**: Python 3.11+ support with native union types
- **Developer experience**: Type safety with mypy, comprehensive testing

See [CHANGELOG.md](CHANGELOG.md) for complete details.
