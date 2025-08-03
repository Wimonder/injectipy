# Injectipy Examples

Code examples for the Injectipy dependency injection library using scope-based management.

## Examples Overview

### 1. `basic_usage.py`
Fundamental patterns:
- Register static values and factory functions
- Singleton pattern with `evaluate_once=True`
- Class constructor injection
- Type-based dependency keys

**Run it:**
```bash
python examples/basic_usage.py
```

### 2. `advanced_patterns.py`
Complex patterns:
- Protocol-based dependency injection
- Configuration-driven factories
- Multi-layer service architecture
- Factory pattern with DI

**Run it:**
```bash
python examples/advanced_patterns.py
```

### 3. `testing_patterns.py`
Testing strategies:
- Isolated scope testing
- Mock dependencies
- Integration testing with real dependencies
- Pytest fixtures for scope setup

**Run it:**
```bash
python examples/testing_patterns.py
```

### 4. `async_patterns.py`
Async/await patterns:
- Async context managers
- Async resolvers and factory functions
- Concurrent async tasks with proper isolation
- Mixed sync/async dependency resolution

**Run it:**
```bash
python examples/async_patterns.py
```

## Common Patterns Summary

### 1. Basic Registration
```python
from injectipy import DependencyScope, inject, Inject

# Create a scope
scope = DependencyScope()

# Register static values
scope.register_value("config", {"debug": True})

# Register factory functions
scope.register_resolver("service", lambda: MyService())

# Use in functions within scope context
@inject
def my_function(config: dict = Inject["config"]):
    return config["debug"]

with scope:
    result = my_function()  # Automatic injection
```

### 2. Type-based Dependencies
```python
from typing import Protocol
from injectipy import DependencyScope, inject, Inject

class ServiceProtocol(Protocol):
    def do_work(self) -> str: ...

class MyService:
    def do_work(self) -> str:
        return "work done"

# Create scope and register with type as key
scope = DependencyScope()
scope.register_value(ServiceProtocol, MyService())

@inject
def worker(service: ServiceProtocol = Inject[ServiceProtocol]):
    return service.do_work()

with scope:
    result = worker()  # Automatic injection
```

### 3. Singleton Pattern
```python
from injectipy import DependencyScope

class ExpensiveResource:
    def __init__(self):
        print("Creating expensive resource...")

# Create scope and register with evaluate_once=True for singleton behavior
scope = DependencyScope()
scope.register_resolver(
    "resource",
    ExpensiveResource,
    evaluate_once=True
)

with scope:
    resource1 = scope["resource"]  # Creates instance
    resource2 = scope["resource"]  # Reuses same instance
    assert resource1 is resource2
```

### 4. Async/Await Support
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

### 5. Testing with Mocks
```python
from injectipy import DependencyScope, inject, Inject

# Create isolated scope for testing
test_scope = DependencyScope()

# Register mock dependencies
mock_service = MockService()
test_scope.register_value(ServiceProtocol, mock_service)

# Create object with test dependencies within scope
with test_scope:
    obj = MyClass()  # Dependencies injected automatically
```

## Best Practices

1. **Always use `with scope:` context** for dependency injection
2. **Use protocols** for better testability and loose coupling
3. **Use `evaluate_once=True`** for expensive singleton resources
4. **Create separate scopes** for different contexts (test, prod, etc.)
5. **Register configuration early** in application startup
6. **Use type keys** when possible for better type safety

## Running Examples

All examples are self-contained and can be run directly:

```bash
# Run individual examples
python examples/basic_usage.py
python examples/advanced_patterns.py
python examples/testing_patterns.py

# Or run all examples
cd examples
python basic_usage.py && python advanced_patterns.py && python testing_patterns.py
```

## Example Output

Each example shows:
- Dependency registration and resolution
- Service interactions within scopes
- Test patterns with isolated dependencies
