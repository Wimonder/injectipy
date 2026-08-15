# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-08-16

### Fixed
- **Deadlocks**: Resolvers now run outside the scope lock, so resolver code can use other threads and scopes can resolve into each other
- **Type contracts**: `@inject` and `@ainject` are overloaded, so decorated functions keep their own type instead of a union, and `@inject(scopes=[...])` type checks
- **`Inject[SomeType]`**: Typed as `SomeType` instead of `Any`, so type checkers verify it against the parameter annotation
- **`@ainject` on classmethods**: Works when applied on top of `@classmethod`, matching `@inject`
- **`is_active()`**: Reports the scope stack of the current thread or task instead of a shared flag
- **Out-of-order exit**: A scope exited out of order is removed from its own position on the stack
- **Resolver dependencies**: Resolved from the owning scope when no scope is active, instead of failing
- **Builtin resolvers**: Callables without an introspectable signature, such as `dict`, can be registered as resolvers

### Added
- **`replace=True`**: Replace an existing registration on all `register_*` methods
- **`unregister(key)` and `clear()`**: Remove one or all dependencies from a scope

### Changed
- **Performance**: Signatures are inspected once at decoration time, cutting per call injection overhead by about 4x
- **Decorator compatibility**: `@inject` now injects through `@contextmanager`, `@lru_cache` and other `functools.wraps` decorators

### Breaking Changes
- **Missing resolver dependencies**: Resolving a resolver whose dependency is missing raises `DependencyNotFoundError` instead of passing the `Inject` marker

## [0.4.0] - 2026-08-15

### Fixed
- **Scope reuse**: Exiting a scope no longer clears its registry, so a scope can be entered again ([#14](https://github.com/Wimonder/injectipy/issues/14))

### Breaking Changes
- **Registrations persist**: Registering the same key again in a reused scope raises `DuplicateRegistrationError`, where the registry used to be cleared on exit. Use `replace=True` or `clear()` from 0.5.0

### Changed
- **Python support**: Tested against Python 3.11, 3.12, 3.13 and 3.14 in CI
- **Dependencies**: Updated development dependencies (pytest 9, mypy 2, black 26, ruff 0.16, pre-commit 4, mkdocstrings 1)

## [0.3.0] - 2025-08-03

### Added
- **`@ainject` decorator**: Clean async dependency injection that automatically awaits async dependencies
- **`AsyncDependencyError`**: Clear error messages guiding users to use correct decorator
- **Strict async/sync separation**: `@inject` rejects async dependencies, `@ainject` handles them properly
- **Performance optimizations**: Cached async resolver detection for better runtime performance

### Breaking Changes
- **`@inject` behavior change**: Now rejects async dependencies with clear error messages (use `@ainject` instead)

### Enhanced
- **Error messages**: More concise and actionable guidance for developers
- **Code quality**: Reduced duplication and improved type safety
- **Documentation**: Comprehensive async/await examples and usage patterns

### Technical
- Added async resolver caching in `DependencyScope` for performance
- Extracted helper functions to reduce code duplication
- Enhanced type annotations for better static analysis

## [0.2.0] - 2025-08-03

### Added
- **Async/Await Support**: `DependencyScope` now supports both `with` and `async with` context managers
- **Async Resolvers**: New `register_async_resolver()` method for async factory functions
- **Context Isolation**: Enhanced thread and async task isolation using `contextvars`
- **Async Utilities**: `run_with_scope_context()` and `gather_with_scope_isolation()` helper functions

### Enhanced
- **Threading Support**: Improved scope management with better async task isolation
- **Concurrency Safety**: Eliminates race conditions in concurrent async scenarios

### Technical
- Uses `contextvars.ContextVar` instead of `threading.local` for scope stack management
- Zero breaking changes

## [0.1.0] - 2024-01-20

### Added
- `@inject` decorator for automatic dependency injection
- `Inject[key]` type-safe parameter markers
- `DependencyScope` context manager for explicit scope management
- Thread-safe dependency registration and resolution
- Circular dependency detection at registration time
- Lazy evaluation with optional caching (`evaluate_once=True`)
- Support for keyword-only parameters and method chaining
- Full mypy compatibility with Python 3.11+ typing syntax
- Clear error messages and exception hierarchy

### Requirements
- Python 3.11+
- No external dependencies

[0.5.0]: https://github.com/Wimonder/injectipy/releases/tag/v0.5.0
[0.4.0]: https://github.com/Wimonder/injectipy/releases/tag/v0.4.0
[0.3.0]: https://github.com/Wimonder/injectipy/releases/tag/v0.3.0
[0.2.0]: https://github.com/Wimonder/injectipy/releases/tag/v0.2.0
[0.1.0]: https://github.com/Wimonder/injectipy/releases/tag/v0.1.0
