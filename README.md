# Injectipy

A dependency injection library for Python that uses explicit scopes instead of global state. Provides type-safe dependency resolution with circular dependency detection.

[![PyPI version](https://badge.fury.io/py/injectipy.svg)](https://badge.fury.io/py/injectipy)
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Type Checked](https://img.shields.io/badge/typed-mypy-blue.svg)](https://mypy.readthedocs.io/)

## Key Features

- **Explicit scopes**: Dependencies managed within context managers, no global state
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

### Type Safety

Works with mypy for static type checking:

```python
from typing import Protocol
from injectipy import inject, Inject, DependencyScope

class DatabaseProtocol(Protocol):
    def query(self, sql: str) -> list: ...

class PostgreSQLDatabase:
    def query(self, sql: str) -> list:
        return ["result1", "result2"]

# Create scope and register with type hints
scope = DependencyScope()
scope.register_value("database", PostgreSQLDatabase())

@inject
def get_users(db: DatabaseProtocol = Inject["database"]) -> list:
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
from injectipy import inject, Inject, DependencyScope
from injectipy import DependencyNotFoundError, CircularDependencyError, DuplicateRegistrationError

# Missing dependency
@inject
def missing_dep(value: str = Inject["nonexistent"]):
    return value

try:
    missing_dep()
except DependencyNotFoundError as e:
    print(e)  # "Dependency 'nonexistent' not found"

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

## API Reference

### Core Components

#### `@inject` decorator
Decorates functions/methods to enable automatic dependency injection within active scopes.

#### `Inject[key]`
Type-safe dependency marker for function parameters.

#### `DependencyScope`
Context manager for managing dependency lifecycles and isolation.

### DependencyScope Methods

#### `register_value(key, value)`
Register a static value as a dependency. Returns self for method chaining.

#### `register_resolver(key, resolver, *, evaluate_once=False)`
Register a factory function as a dependency. Returns self for method chaining.
- `evaluate_once=True`: Cache the result after first evaluation (singleton pattern)

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

### Version 0.1.0 (2024-01-20)
- **Initial release** of Injectipy dependency injection library
- **Core features**: `@inject` decorator, `Inject[key]` markers, `DependencyScope` context managers
- **Advanced capabilities**: Thread safety, circular dependency detection, lazy evaluation
- **Modern Python**: Python 3.11+ support with native union types
- **Developer experience**: Type safety with mypy, comprehensive testing

See [CHANGELOG.md](CHANGELOG.md) for complete details.
