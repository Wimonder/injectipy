# Injectipy

A lightweight, thread-safe dependency injection library for Python with support for circular dependency detection and type safety.

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Type Checked](https://img.shields.io/badge/typed-mypy-blue.svg)](https://mypy.readthedocs.io/)

## Features

- **Thread-safe**: Singleton pattern with proper locking for concurrent access
- **Circular dependency detection**: Prevents runtime errors with dependency cycle analysis
-  **Type-safe**: Full mypy compatibility with strict type checking
- **Forward references**: Register dependencies in any order
- **Simple API**: Clean decorator-based injection with minimal boilerplate
- **Lazy evaluation**: Dependencies resolved only when needed
- **Test-friendly**: Built-in test isolation support

## Installation

```bash
pip install injectipy
```

## Quick Start

### Basic Usage

```python
from injectipy import inject, Inject, injectipy_store

# Register a simple value
injectipy_store.register_value("database_url", "postgresql://localhost/mydb")

# Register a factory function
def create_database_connection(database_url: str = Inject["database_url"]):
    return f"Connected to {database_url}"

injectipy_store.register_resolver("db_connection", create_database_connection)

# Use dependency injection in your functions
@inject
def get_user(user_id: int, db_connection: str = Inject["db_connection"]):
    return f"User {user_id} from {db_connection}"

# Call the function - dependencies are automatically injected
user = get_user(123)
print(user)  # "User 123 from Connected to postgresql://localhost/mydb"
```

### Class-based Injection

```python
from injectipy import inject, Inject, injectipy_store

class UserService:
    @inject
    def __init__(self, db_connection: str = Inject["db_connection"]):
        self.db = db_connection

    def get_user(self, user_id: int):
        return f"User {user_id} from {self.db}"

# Dependencies are injected automatically
service = UserService()
print(service.get_user(456))
```

### Factory Functions with Dependencies

```python
from injectipy import inject, Inject, injectipy_store

# Register configuration
injectipy_store.register_value("api_key", "secret123")
injectipy_store.register_value("base_url", "https://api.example.com")

# Factory function that depends on other registered dependencies
def create_api_client(
    api_key: str = Inject["api_key"],
    base_url: str = Inject["base_url"]
):
    return f"APIClient(key={api_key}, url={base_url})"

# Register the factory
injectipy_store.register_resolver("api_client", create_api_client)

# Use in your code
@inject
def fetch_data(client = Inject["api_client"]):
    return f"Fetching data with {client}"

print(fetch_data())
```

### Singleton Pattern with `evaluate_once`

```python
from injectipy import injectipy_store
import time

def expensive_resource():
    print("Creating expensive resource...")
    time.sleep(1)  # Simulate expensive operation
    return "ExpensiveResource"

# Register with evaluate_once=True for singleton behavior
injectipy_store.register_resolver(
    "expensive_resource",
    expensive_resource,
    evaluate_once=True
)

# First access creates the resource
resource1 = injectipy_store["expensive_resource"]  # Prints "Creating..."
resource2 = injectipy_store["expensive_resource"]  # No print, reuses cached

assert resource1 is resource2  # Same instance
```

## Advanced Features

### Keyword-Only Parameters

Injectipy also supports keyword-only parameters with Inject:

```python
from injectipy import inject, Inject, injectipy_store

# Register dependencies
injectipy_store.register_value("database", "ProductionDB")
injectipy_store.register_value("cache", "RedisCache")

@inject
def process_data(data: str, *, db=Inject["database"], cache=Inject["cache"], debug=False):
    return f"Processing {data} with {db}, {cache}, debug={debug}"

# Keyword-only parameters work seamlessly
result = process_data("user_data")
print(result)  # "Processing user_data with ProductionDB, RedisCache, debug=False"

# Override specific parameters
result = process_data("user_data", cache="MemoryCache", debug=True)
print(result)  # "Processing user_data with ProductionDB, MemoryCache, debug=True"
```

### Type Safety

Injectipy is fully type-safe and works seamlessly with mypy:

```python
from typing import Protocol
from injectipy import inject, Inject, injectipy_store

class DatabaseProtocol(Protocol):
    def query(self, sql: str) -> list: ...

class PostgreSQLDatabase:
    def query(self, sql: str) -> list:
        return ["result1", "result2"]

# Register with type hints
injectipy_store.register_value("database", PostgreSQLDatabase())

@inject
def get_users(db: DatabaseProtocol = Inject["database"]) -> list:
    return db.query("SELECT * FROM users")

# mypy will verify types correctly
users: list = get_users()
```


### Multiple Stores

While there's a default global store, you can create isolated stores:

```python
from injectipy import InjectipyStore, inject, Inject

# Create custom store
my_store = InjectipyStore()
my_store.register_value("config", {"env": "test"})

# Use with custom store (you'll need to manage the store yourself)
@inject
def my_function(config: dict = Inject["config"]):
    return config

# Note: Custom stores require manual management
# The global injectipy_store is recommended for most use cases
```

## Error Handling

### Missing Dependencies

```python
from injectipy import inject, Inject

@inject
def function_with_missing_dep(missing: str = Inject["nonexistent"]):
    return missing

try:
    function_with_missing_dep()
except KeyError as e:
    print(f"Dependency not found: {e}")
```

### Circular Dependencies

Injectipy automatically detects circular dependencies at registration time:

```python
from injectipy import injectipy_store, Inject

def service_a(b = Inject["service_b"]):
    return f"A depends on {b}"

def service_b(a = Inject["service_a"]):
    return f"B depends on {a}"

injectipy_store.register_resolver("service_a", service_a)

try:
    # This will raise ValueError: Circular dependency detected
    injectipy_store.register_resolver("service_b", service_b)
except ValueError as e:
    print(f"Error: {e}")
```

## Testing

Injectipy provides test isolation through the global store:

```python
import pytest
from injectipy import injectipy_store, inject, Inject

@pytest.fixture(autouse=True)
def reset_store():
    """Reset the store before each test"""
    injectipy_store._reset_for_testing()

def test_dependency_injection():
    injectipy_store.register_value("test_value", "hello")

    @inject
    def test_function(value: str = Inject["test_value"]):
        return value

    assert test_function() == "hello"

def test_isolation():
    # Store is automatically reset, so "test_value" from previous test is gone
    with pytest.raises(KeyError):
        injectipy_store["test_value"]
```

## Thread Safety

Injectipy is fully thread-safe and can be used in concurrent applications:

```python
import threading
from injectipy import injectipy_store, inject, Inject

# Register shared dependency
injectipy_store.register_value("shared_resource", "ThreadSafeResource")

@inject
def worker_function(resource: str = Inject["shared_resource"]):
    return f"Worker using {resource}"

# Safe to use across multiple threads
threads = []
for i in range(10):
    thread = threading.Thread(target=lambda: print(worker_function()))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()
```

## API Reference

### Core Components

#### `@inject` decorator
Decorates functions/methods to enable automatic dependency injection.

#### `Inject[key]`
Type-safe dependency marker for function parameters.

#### `injectipy_store`
Global singleton store for dependency registration and resolution.

### Store Methods

#### `register_value(key, value)`
Register a static value as a dependency.

#### `register_resolver(key, resolver, *, evaluate_once=False)`
Register a factory function as a dependency.
- `evaluate_once=True`: Cache the result after first evaluation (singleton pattern)

#### `[key]` (getitem)
Resolve and return a dependency by key.

#### `_reset_for_testing()`
Clear all registered dependencies (for testing only).

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

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
poetry run flake8 injectipy/
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=injectipy

# Run specific test categories
poetry run pytest tests/test_thread_safety.py  # Thread safety tests
poetry run pytest tests/test_circular_dependencies.py  # Circular dependency tests
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### Version 0.1.0
- Initial release
- Thread-safe singleton pattern
- Circular dependency detection
- Type safety with mypy
- Comprehensive test coverage
