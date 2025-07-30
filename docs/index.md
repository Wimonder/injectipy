# Injectipy

A lightweight, thread-safe dependency injection library for Python that provides clean, type-safe dependency management with minimal boilerplate.

[![PyPI version](https://badge.fury.io/py/injectipy.svg)](https://badge.fury.io/py/injectipy)
[![Python versions](https://img.shields.io/pypi/pyversions/injectipy.svg)](https://pypi.org/project/injectipy/)
[![License](https://img.shields.io/github/license/Wimonder/injectipy.svg)](https://github.com/Wimonder/injectipy/blob/main/LICENSE)
[![Tests](https://github.com/Wimonder/injectipy/workflows/CI/badge.svg)](https://github.com/Wimonder/injectipy/actions)
[![Coverage](https://codecov.io/gh/Wimonder/injectipy/branch/main/graph/badge.svg)](https://codecov.io/gh/Wimonder/injectipy)

## Features

✨ **Simple & Intuitive**: Clean API with minimal learning curve
🔒 **Thread-Safe**: Built for concurrent applications
🏷️ **Type-Safe**: Full mypy support with generic type hints
🔄 **Circular Detection**: Automatic circular dependency detection
⚡ **High Performance**: Optimized for speed with optional caching
🧪 **Test-Friendly**: Easy mocking and test isolation

## Quick Example

```python
from injectipy import inject, Inject, injectipy_store

# Register dependencies
injectipy_store.register_value("config", {"database_url": "sqlite:///app.db"})
injectipy_store.register_resolver("database", lambda: Database())

# Use dependency injection
@inject
def create_user(name: str, config: dict = Inject["config"], db: Database = Inject["database"]):
    return User.create(name, config["database_url"], db)

# Dependencies are automatically injected
user = create_user("Alice")
```

## Why Injectipy?

### 🚀 **Lightweight & Fast**
No heavy frameworks or complex configuration. Just clean, fast dependency injection.

### 🔧 **Developer Friendly**
Intuitive API that works with your existing code. No need to restructure your application.

### 🛡️ **Production Ready**
Thread-safe, battle-tested, with comprehensive error handling and validation.

### 🎯 **Type Safe**
Full static type checking support. Catch dependency issues at development time, not runtime.

## Installation

```bash
pip install injectipy
```

Or with Poetry:

```bash
poetry add injectipy
```

## Getting Started

1. **[Installation](installation.md)** - Install injectipy in your project
2. **[Quick Start](quickstart.md)** - Get up and running in 5 minutes
3. **[Basic Usage](basic-usage.md)** - Learn the core concepts
4. **[Advanced Patterns](advanced-patterns.md)** - Explore powerful features

## Core Components

### `@inject` Decorator
Enable dependency injection on any function:

```python
@inject
def my_function(service: MyService = Inject["service"]):
    return service.do_something()
```

### `Inject[key]` Marker
Type-safe parameter markers for dependency injection:

```python
def process_data(
    data: list,
    config: dict = Inject["config"],  # Inject by key
    logger = Inject["logger"]         # Automatic type inference
):
    pass
```

### `InjectipyStore` Container
Thread-safe dependency container:

```python
from injectipy import injectipy_store

# Register values
injectipy_store.register_value("api_key", "secret")

# Register factory functions
injectipy_store.register_resolver("service", lambda: MyService())

# Register with caching
injectipy_store.register_resolver("db", create_database, cache=True)
```

## Use Cases

- **Web Applications**: Inject database connections, configuration, services
- **CLI Tools**: Manage application configuration and resources
- **Testing**: Easy mocking and test isolation
- **Microservices**: Clean dependency management across services
- **Data Processing**: Inject processors, validators, and transformers

## Community & Support

- 📖 **[Documentation](https://wimonder.github.io/injectipy/)**
- 🐛 **[Issue Tracker](https://github.com/Wimonder/injectipy/issues)**
- 💬 **[Discussions](https://github.com/Wimonder/injectipy/discussions)**
- 📦 **[PyPI Package](https://pypi.org/project/injectipy/)**

## License

MIT License - see [LICENSE](https://github.com/Wimonder/injectipy/blob/main/LICENSE) for details.
