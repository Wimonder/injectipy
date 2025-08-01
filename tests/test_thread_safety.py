import concurrent.futures
import threading
import time

from injectipy import DependencyScope


def test_scope_thread_safety():
    """Test that scope creation is thread-safe."""
    instances = []

    def create_instance():
        scope = DependencyScope()
        instances.append(scope)

    threads = []
    for _ in range(10):
        thread = threading.Thread(target=create_instance)
        threads.append(thread)

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    # Each should be a separate instance (scopes are not singletons)
    assert len({id(instance) for instance in instances}) == 10


def test_concurrent_registration():
    """Test that concurrent registration is thread-safe."""
    store = DependencyScope()
    results = []
    errors = []

    # Use timestamp to ensure unique keys across test runs
    import time

    timestamp = str(int(time.time() * 1000000))

    def register_value(key: str, value: str):
        try:
            store.register_value(key, value)
            results.append((key, value))
        except Exception as e:
            errors.append((key, str(e)))

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i in range(100):
            future = executor.submit(register_value, f"reg_key_{timestamp}_{i}", f"value_{i}")
            futures.append(future)

        concurrent.futures.wait(futures)

    # All registrations should succeed
    assert len(errors) == 0
    assert len(results) == 100

    # Verify all values are correctly stored
    for key, expected_value in results:
        assert store[key] == expected_value


def test_concurrent_access():
    """Test that concurrent access to the store is thread-safe."""
    store = DependencyScope()

    # Pre-register some values with unique keys
    import time

    timestamp = str(int(time.time() * 1000000))
    for i in range(10):
        store.register_value(f"access_key_{timestamp}_{i}", f"value_{i}")

    results = []
    errors = []

    def access_value(key: str):
        try:
            value = store[key]
            results.append((key, value))
        except Exception as e:
            errors.append((key, str(e)))

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for _ in range(100):
            for i in range(10):
                future = executor.submit(access_value, f"access_key_{timestamp}_{i}")
                futures.append(future)

        concurrent.futures.wait(futures)

    # All accesses should succeed
    assert len(errors) == 0
    assert len(results) == 1000

    # Verify all values are correct
    for key, value in results:
        expected_idx = key.split("_")[-1]
        expected_value = f"value_{expected_idx}"
        assert value == expected_value


def test_concurrent_resolver_execution():
    """Test that concurrent resolver execution is thread-safe."""
    store = DependencyScope()
    execution_count = 0
    execution_lock = threading.Lock()

    # Use timestamp for unique key
    timestamp = str(int(time.time() * 1000000))
    resolver_key = f"slow_key_{timestamp}"

    def slow_resolver():
        nonlocal execution_count
        time.sleep(0.01)  # Simulate slow operation
        with execution_lock:
            execution_count += 1
        return f"result_{execution_count}"

    store.register_resolver(resolver_key, slow_resolver)

    results = []

    def get_value():
        value = store[resolver_key]
        results.append(value)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for _ in range(20):
            future = executor.submit(get_value)
            futures.append(future)

        concurrent.futures.wait(futures)

    # All resolvers should have executed (no caching)
    assert len(results) == 20
    assert execution_count == 20


def test_concurrent_evaluate_once_resolver():
    """Test that evaluate_once resolvers are thread-safe and only execute once."""
    store = DependencyScope()
    execution_count = 0
    execution_lock = threading.Lock()

    # Use timestamp for unique key
    timestamp = str(int(time.time() * 1000000))
    cached_key = f"cached_key_{timestamp}"

    def slow_resolver():
        nonlocal execution_count
        time.sleep(0.01)  # Simulate slow operation
        with execution_lock:
            execution_count += 1
        return f"cached_result_{execution_count}"

    store.register_resolver(cached_key, slow_resolver, evaluate_once=True)

    results = []

    def get_value():
        value = store[cached_key]
        results.append(value)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for _ in range(20):
            future = executor.submit(get_value)
            futures.append(future)

        concurrent.futures.wait(futures)

    # Resolver should have executed only once
    assert execution_count == 1
    # All results should be the same
    assert len(set(results)) == 1
    assert all(result == "cached_result_1" for result in results)


def test_concurrent_mixed_operations():
    """Test concurrent registration and access operations."""
    store = DependencyScope()
    results = []
    errors = []

    def register_and_access(worker_id: int):
        try:
            # Register some values
            for i in range(5):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"
                store.register_value(key, value)

            # Access previously registered values (if any)
            for i in range(max(0, worker_id - 1)):
                for j in range(5):
                    key = f"worker_{i}_key_{j}"
                    try:
                        value = store[key]
                        results.append((key, value))
                    except KeyError:
                        # Key might not exist yet, that's ok
                        pass
        except Exception as e:
            errors.append((worker_id, str(e)))

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for worker_id in range(10):
            future = executor.submit(register_and_access, worker_id)
            futures.append(future)

        concurrent.futures.wait(futures)

    # No errors should occur
    assert len(errors) == 0

    # Verify some registrations worked
    assert len(results) > 0
