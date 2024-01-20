# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/Wimonder/injectipy/releases/tag/v0.1.0
