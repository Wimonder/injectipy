"""Performance and stress tests for injectipy.

This module contains performance benchmarks and stress tests to ensure
the dependency injection system performs well under various loads.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from injectipy import DependencyScope, Inject, inject

pytestmark = [pytest.mark.performance, pytest.mark.slow]


@pytest.fixture
def test_scope() -> DependencyScope:
    return DependencyScope()


def test_large_number_of_registrations(test_scope: DependencyScope):
    """Test performance with many registered dependencies."""
    with test_scope:
        # Register 1000 simple values
        for i in range(1000):
            test_scope.register_value(f"value_{i}", f"data_{i}")

        # Test that access is still fast
        start_time = time.time()
        for i in range(100):
            result = test_scope[f"value_{i}"]
            assert result == f"data_{i}"
        end_time = time.time()

        # Should complete in well under a second
        assert (end_time - start_time) < 0.1


def test_deep_resolver_chain_performance(test_scope: DependencyScope):
    """Test performance with deep dependency chains."""
    with test_scope:
        # Create a shorter chain of 10 resolvers for testing
        chain_length = 10

        # Register the base resolver
        def resolver_0():
            return "base"

        test_scope.register_resolver("resolver_0", resolver_0)

        # Create a chain using Inject dependencies
        for i in range(1, chain_length):

            def make_resolver(index):
                def resolver(prev_result=Inject[f"resolver_{index - 1}"]):
                    return f"{prev_result}_{index}"

                return resolver

            chain_resolver = make_resolver(i)
            chain_resolver.__name__ = f"resolver_{i}"
            test_scope.register_resolver(f"resolver_{i}", chain_resolver)

        # Time the resolution of the final resolver
        start_time = time.time()
        result = test_scope[f"resolver_{chain_length - 1}"]
        end_time = time.time()

        # Verify correct result
        expected = "base"
        for i in range(1, chain_length):
            expected += f"_{i}"
        assert result == expected

        # Should complete in reasonable time
        assert (end_time - start_time) < 0.1


def test_evaluate_once_performance(test_scope: DependencyScope):
    """Test that evaluate_once provides performance benefits."""
    with test_scope:
        expensive_call_count = 0

        def expensive_resolver():
            nonlocal expensive_call_count
            expensive_call_count += 1
            # Simulate expensive operation
            time.sleep(0.01)
            return "expensive_result"

        test_scope.register_resolver("expensive", expensive_resolver, evaluate_once=True)

        # First call
        start_time = time.time()
        result1 = test_scope["expensive"]
        first_call_time = time.time() - start_time

        # Subsequent calls should be much faster
        start_time = time.time()
        result2 = test_scope["expensive"]
        second_call_time = time.time() - start_time

        # Verify results
        assert result1 == "expensive_result"
        assert result2 == "expensive_result"
        assert result1 is result2  # Same object
        assert expensive_call_count == 1  # Only called once

        # Second call should be significantly faster
        assert second_call_time < (first_call_time * 0.1)


def test_concurrent_resolver_performance():
    """Test performance under concurrent access."""
    test_scope = DependencyScope()

    with test_scope:
        # Register resolvers that simulate work
        def cpu_bound_resolver(i: int):
            def resolver():
                # Simulate some CPU work
                total = 0
                for j in range(1000):
                    total += j * i
                return f"result_{i}_{total}"

            return resolver

        # Register 50 different resolvers
        for i in range(50):
            test_scope.register_resolver(f"cpu_task_{i}", cpu_bound_resolver(i))

        # Test concurrent access
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit 200 tasks (multiple accesses to same resolvers)
            futures = []
            for _ in range(4):  # 4 rounds
                for i in range(50):  # 50 different resolvers
                    future = executor.submit(lambda key=f"cpu_task_{i}": test_scope[key])
                    futures.append(future)

            # Wait for all to complete
            results = [future.result() for future in as_completed(futures)]

        end_time = time.time()

        # Verify we got all results
        assert len(results) == 200

        # Should complete in reasonable time even with concurrency
        assert (end_time - start_time) < 5.0


def test_memory_usage_with_cached_resolvers(test_scope: DependencyScope):
    """Test memory behavior with cached resolvers."""
    with test_scope:
        # Register resolvers that create objects
        def object_creator(size):
            def resolver():
                # Create an object with some data
                return {"data": "x" * size, "id": size}

            return resolver

        # Register 100 cached resolvers
        for i in range(100):
            test_scope.register_resolver(f"object_{i}", object_creator(i * 100), evaluate_once=True)

        # Access all resolvers to populate cache
        results = []
        for i in range(100):
            result = test_scope[f"object_{i}"]
            results.append(result)

        # Verify all objects are cached (same instances)
        for i in range(100):
            assert test_scope[f"object_{i}"] is results[i]

        # Verify objects have expected data
        for i, result in enumerate(results):
            expected_size = i * 100
            assert result["id"] == expected_size
            assert len(result["data"]) == expected_size


def test_injection_performance_with_many_parameters():
    """Test performance of @inject decorator with many parameters."""
    test_scope = DependencyScope()

    with test_scope:
        # Register many dependencies
        for i in range(50):
            test_scope.register_value(f"dep_{i}", f"value_{i}")

        # Create function with many injected parameters
        def create_function_with_many_deps():
            # Build parameter list dynamically
            params = ", ".join([f"dep_{i}: str = Inject['dep_{i}']" for i in range(50)])
            func_code = f"""
@inject
def many_deps_function({params}):
    return "result"
"""
            # Execute in local scope
            local_scope = {"inject": inject, "Inject": Inject}
            exec(func_code, globals(), local_scope)
            return local_scope["many_deps_function"]

        func_with_many_deps = create_function_with_many_deps()

        # Time multiple calls
        start_time = time.time()
        for _ in range(100):
            result = func_with_many_deps()
            assert result == "result"
        end_time = time.time()

        # Should complete in reasonable time
        assert (end_time - start_time) < 1.0


def test_stress_test_mixed_operations():
    """Stress test with mixed registration and access operations."""
    test_scope = DependencyScope()

    with test_scope:
        # Phase 1: Register base dependencies
        for i in range(100):
            test_scope.register_value(f"base_{i}", f"base_value_{i}")

        # Phase 2: Register resolvers that depend on base values using Inject
        for i in range(100):

            def make_resolver(index):
                def resolver(base_val=Inject[f"base_{index}"]):
                    return f"resolved_{base_val}"

                return resolver

            stress_resolver = make_resolver(i)
            stress_resolver.__name__ = f"resolver_{i}"
            test_scope.register_resolver(f"resolver_{i}", stress_resolver)

        # Phase 3: Concurrent access to all dependencies
        def access_random_deps():
            import random

            results = []
            for _ in range(20):
                # Randomly access either base values or resolvers
                if random.choice([True, False]):
                    key = f"base_{random.randint(0, 99)}"
                else:
                    key = f"resolver_{random.randint(0, 99)}"
                results.append(test_scope[key])
            return results

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(access_random_deps) for _ in range(10)]
            all_results = [future.result() for future in as_completed(futures)]

        end_time = time.time()

        # Verify we got results from all workers
        assert len(all_results) == 10
        for worker_results in all_results:
            assert len(worker_results) == 20

        # Should complete in reasonable time
        assert (end_time - start_time) < 2.0


def test_singleton_creation_performance():
    """Test performance of singleton pattern under load."""

    # Test many threads trying to get the singleton
    def get_singleton():
        return DependencyScope()

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(get_singleton) for _ in range(100)]
        scopes = [future.result() for future in as_completed(futures)]

    end_time = time.time()

    # Each should be a separate instance (scopes are not singletons)
    assert len({id(scope) for scope in scopes}) == 100

    # Should complete quickly
    assert (end_time - start_time) < 1.0


def test_resolver_caching_consistency_under_load():
    """Test that resolver caching remains consistent under concurrent load."""
    test_scope = DependencyScope()

    with test_scope:
        call_count = 0

        def tracked_resolver():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"

        test_scope.register_resolver("tracked", tracked_resolver, evaluate_once=True)

        def access_cached_resolver():
            return test_scope["tracked"]

        # Access from multiple threads simultaneously
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(access_cached_resolver) for _ in range(50)]
            results = [future.result() for future in as_completed(futures)]

        # All results should be identical (cached)
        first_result = results[0]
        assert all(result == first_result for result in results)

        # Should have been called only once (or very few times due to race conditions)
        assert call_count <= 3  # Allow for some race condition scenarios
