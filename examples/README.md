# Injectipy Examples

This directory contains comprehensive examples demonstrating various patterns and use cases for the Injectipy dependency injection library.

## Examples Overview

### 1. `basic_usage.py`
Demonstrates fundamental Injectipy patterns:
- **Simple Values**: Register and inject configuration values
- **Factory Functions**: Use factory functions as dependencies
- **Singleton Pattern**: Create singleton dependencies with `evaluate_once=True`
- **Class Constructor Injection**: Inject dependencies into class constructors
- **Type-based Keys**: Use Python types as dependency keys
- **Parameter Name Injection**: Automatic injection by matching parameter names

**Run it:**
```bash
python examples/basic_usage.py
```

### 2. `advanced_patterns.py`
Shows sophisticated dependency injection patterns:
- **Protocol-based DI**: Use protocols for loose coupling
- **Configuration-based Factories**: Create dependencies from configuration
- **Layered Architecture**: Build complex service layers with DI
- **Factory Dependencies**: Use factories to create specialized instances

**Key concepts:**
- Protocol-based dependency injection for better testability
- Configuration management with dependency injection
- Multi-layer service architecture
- Factory pattern with dependency injection

**Run it:**
```bash
python examples/advanced_patterns.py
```

### 3. `testing_patterns.py`
Demonstrates testing strategies with dependency injection:
- **Isolated Store Testing**: Use separate stores for test isolation
- **Mock Dependencies**: Replace real services with mocks for testing
- **Integration Testing**: Test with real dependencies
- **Pytest Fixtures**: Use pytest fixtures for reusable test setup

**Key concepts:**
- Test isolation with separate dependency stores
- Mocking external services and databases
- Unit vs integration testing approaches
- Fixture-based test organization

**Run it:**
```bash
python examples/testing_patterns.py
```

## Common Patterns Summary

### 1. Basic Registration
```python
from injectipy import injectipy_store, inject, Inject

# Register static values
injectipy_store.register_value("config", {"debug": True})

# Register factory functions
injectipy_store.register_resolver("service", lambda: MyService())

# Use in functions
@inject
def my_function(config: dict = Inject["config"]):
    return config["debug"]
```

### 2. Type-based Dependencies
```python
from typing import Protocol

class ServiceProtocol(Protocol):
    def do_work(self) -> str: ...

class MyService:
    def do_work(self) -> str:
        return "work done"

# Register with type as key
injectipy_store.register_value(ServiceProtocol, MyService())

@inject
def worker(service: ServiceProtocol = Inject[ServiceProtocol]):
    return service.do_work()
```

### 3. Singleton Pattern
```python
class ExpensiveResource:
    def __init__(self):
        print("Creating expensive resource...")

# Register with evaluate_once=True for singleton behavior
injectipy_store.register_resolver(
    "resource", 
    ExpensiveResource,
    evaluate_once=True
)
```

### 4. Testing with Mocks
```python
# Create isolated store for testing
test_store = InjectipyStore()

# Register mock dependencies
mock_service = MockService()
test_store.register_value(ServiceProtocol, mock_service)

# Create object with test dependencies
obj = MyClass(service=test_store[ServiceProtocol])
```

## Best Practices

1. **Use Protocols**: Define interfaces with protocols for better testability
2. **Prefer Type Keys**: Use types as keys when possible for better type safety
3. **Singleton Pattern**: Use `evaluate_once=True` for expensive resources
4. **Test Isolation**: Use separate stores or mocks for testing
5. **Configuration**: Register configuration early in application startup
6. **Factory Pattern**: Use factories for complex object creation

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

Each example produces detailed output showing:
- Dependency registration
- Automatic injection in action
- Service interactions
- Test execution results

The examples are designed to be educational and demonstrate real-world usage patterns you can apply in your own applications.