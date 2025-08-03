# Injectipy

A Python dependency injection library using explicit scopes instead of global state. Provides type-safe dependency resolution with circular dependency detection.

[![PyPI version](https://badge.fury.io/py/injectipy.svg)](https://badge.fury.io/py/injectipy)
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/Wimonder/injectipy.svg)](https://github.com/Wimonder/injectipy/blob/main/LICENSE)
[![Tests](https://github.com/Wimonder/injectipy/workflows/CI/badge.svg)](https://github.com/Wimonder/injectipy/actions)

## Features

- **Explicit scopes**: Dependencies managed within context managers, no global state
- **Type safety**: Works with mypy for static type checking
- **Circular dependency detection**: Detects dependency cycles at registration time
- **Thread safety**: Each scope is isolated, safe for concurrent use
- **Lazy evaluation**: Dependencies resolved only when accessed
- **Test isolation**: Each test can use its own scope

## Quick Example

```python
from injectipy import inject, Inject, DependencyScope

# Create a dependency scope
scope = DependencyScope()

# Register dependencies
scope.register_value("config", {"database_url": "sqlite:///app.db"})
scope.register_resolver("database", lambda: Database())

# Use dependency injection
@inject
def create_user(name: str, config: dict = Inject["config"], db: Database = Inject["database"]):
    return User.create(name, config["database_url"], db)

# Use within scope context for automatic injection
with scope:
    user = create_user("Alice")
```

## Key Characteristics

- **No global state**: Each scope manages its own dependencies
- **Context managers**: Use `with scope:` to activate dependency injection
- **Type checking**: Works with mypy for compile-time validation
- **Thread isolation**: Multiple threads can use separate or shared scopes safely

## Installation

```bash
pip install injectipy
```

Or with Poetry:

```bash
poetry add injectipy
```

## Documentation

- [Installation](installation.md) - Install and verify setup
- Basic usage examples in this document
- [GitHub Examples](https://github.com/Wimonder/injectipy/tree/main/examples) - Practical code examples

## Basic Usage

### Function Injection

```python
from injectipy import inject, Inject, DependencyScope

scope = DependencyScope()
scope.register_value("config", {"debug": True})

@inject
def my_function(config: dict = Inject["config"]):
    return config["debug"]

with scope:
    result = my_function()  # Returns True
```

### Factory Functions

```python
def create_database(host=Inject["db_host"], port=Inject["db_port"]):
    return Database(host, port)

scope = DependencyScope()
scope.register_value("db_host", "localhost")
scope.register_value("db_port", 5432)
scope.register_resolver("database", create_database)

with scope:
    db = scope["database"]  # Factory called with injected dependencies
```

## Use Cases

- **Web Applications**: Inject database connections, configuration, services
- **CLI Tools**: Manage application configuration and resources
- **Testing**: Easy mocking and test isolation
- **Microservices**: Clean dependency management across services
- **Data Processing**: Inject processors, validators, and transformers

## Links

- [GitHub Repository](https://github.com/Wimonder/injectipy)
- [Issue Tracker](https://github.com/Wimonder/injectipy/issues)
- [PyPI Package](https://pypi.org/project/injectipy/)

## License

MIT License - see [LICENSE](https://github.com/Wimonder/injectipy/blob/main/LICENSE) for details.
