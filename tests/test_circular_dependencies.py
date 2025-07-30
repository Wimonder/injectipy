import pytest

from injectipy.models.inject import Inject
from injectipy.store import InjectipyStore


def test_simple_circular_dependency():
    """Test detection of simple A -> B -> A circular dependency."""
    store = InjectipyStore()

    # Use unique keys to avoid conflicts with other tests
    import time

    timestamp = str(int(time.time() * 1000000))
    key_a = f"circular_a_{timestamp}"
    key_b = f"circular_b_{timestamp}"

    def resolver_a(b=Inject[key_b]):
        return f"A with {b}"

    def resolver_b(a=Inject[key_a]):
        return f"B with {a}"

    # Register first resolver
    store.register_resolver(key_a, resolver_a)

    # Registering second resolver should detect circular dependency
    with pytest.raises(ValueError, match="Circular dependency detected"):
        store.register_resolver(key_b, resolver_b)


def test_self_circular_dependency():
    """Test detection of A -> A self-circular dependency."""
    store = InjectipyStore()

    import time

    timestamp = str(int(time.time() * 1000000))
    key_a = f"self_circular_{timestamp}"

    def resolver_a(a=Inject[key_a]):
        return f"A with {a}"

    # Should detect self-dependency
    with pytest.raises(ValueError, match="Circular dependency detected"):
        store.register_resolver(key_a, resolver_a)


def test_complex_circular_dependency():
    """Test detection of A -> B -> C -> A circular dependency."""
    store = InjectipyStore()

    import time

    timestamp = str(int(time.time() * 1000000))
    key_a = f"complex_a_{timestamp}"
    key_b = f"complex_b_{timestamp}"
    key_c = f"complex_c_{timestamp}"

    def resolver_a(b=Inject[key_b]):
        return f"A with {b}"

    def resolver_b(c=Inject[key_c]):
        return f"B with {c}"

    def resolver_c(a=Inject[key_a]):
        return f"C with {a}"

    # Register first two resolvers
    store.register_resolver(key_a, resolver_a)
    store.register_resolver(key_b, resolver_b)

    # Registering third resolver should detect circular dependency
    with pytest.raises(ValueError, match="Circular dependency detected"):
        store.register_resolver(key_c, resolver_c)


def test_no_circular_dependency_with_values():
    """Test that values don't create circular dependencies."""
    store = InjectipyStore()

    import time

    timestamp = str(int(time.time() * 1000000))
    key_a = f"value_a_{timestamp}"
    key_b = f"value_b_{timestamp}"

    # Register values
    store.register_value(key_a, "value_a")
    store.register_value(key_b, "value_b")

    def resolver_c(a=Inject[key_a], b=Inject[key_b]):
        return f"C with {a} and {b}"

    # Should not raise any error
    key_c = f"resolver_c_{timestamp}"
    store.register_resolver(key_c, resolver_c)

    # Should be able to resolve
    result = store[key_c]
    assert result == "C with value_a and value_b"


def test_valid_dependency_chain():
    """Test that valid dependency chains work without false positives."""
    store = InjectipyStore()

    import time

    timestamp = str(int(time.time() * 1000000))
    key_a = f"chain_a_{timestamp}"
    key_b = f"chain_b_{timestamp}"
    key_c = f"chain_c_{timestamp}"

    def resolver_a():
        return "A"

    def resolver_b(a=Inject[key_a]):
        return f"B with {a}"

    def resolver_c(b=Inject[key_b]):
        return f"C with {b}"

    # Should all register successfully
    store.register_resolver(key_a, resolver_a)
    store.register_resolver(key_b, resolver_b)
    store.register_resolver(key_c, resolver_c)

    # Should resolve successfully
    result = store[key_c]
    assert result == "C with B with A"


def test_mixed_inject_dependencies():
    """Test circular dependency with Inject dependencies."""
    store = InjectipyStore()

    import time

    timestamp = str(int(time.time() * 1000000))
    key_a = f"mixed_a_{timestamp}"
    key_b = f"mixed_b_{timestamp}"

    def resolver_a(b=Inject[key_b]):  # Uses Inject to depend on key_b
        return f"A with {b}"

    def resolver_b(a=Inject[key_a]):  # Uses Inject to depend on key_a
        return f"B with {a}"

    # Register first resolver
    store.register_resolver(key_a, resolver_a)

    # This should detect circular dependency
    with pytest.raises(ValueError, match="Circular dependency detected"):
        store.register_resolver(key_b, resolver_b)
