# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Explicit scope management with `DependencyScope` context managers
- Scope isolation for better testability and thread safety
- Context manager protocol for dependency scopes (`with scope:`)
- Method chaining support for scope registration methods
- Support for keyword-only parameters with Inject
- Comprehensive scope functionality tests

### Changed
- **BREAKING**: Replaced global `injectipy_store` with explicit `DependencyScope` instances
- **BREAKING**: All dependency injection now requires active scope context (`with scope:`)
- **BREAKING**: Import changed from `injectipy_store` to `DependencyScope`
- **BREAKING**: Upgraded minimum Python version to 3.11+
- **BREAKING**: Simplified exception hierarchy with basic error messages
- Updated all examples and documentation to use scope-based architecture
- Enhanced thread safety through scope isolation instead of global singleton
- Modernized typing syntax using Python 3.11+ union operator (|)
- Removed complex error messages and suggestions system
- Simplified CI/CD from 5 workflows to single workflow
- Removed unnecessary development scripts and tools

### Deprecated
- Global `injectipy_store` singleton (removed in favor of explicit scopes)
- `InjectipyStore` class (replaced by `DependencyScope`)

### Removed
- Parameter name injection (breaking change - use explicit Inject[key] only)
- Global store pattern and `injectipy_store` singleton
- `InjectipyStore` class from public API
- `_reset_for_testing()` method (replaced by scope isolation)
- typing-extensions dependency (using built-in Python 3.11+ types)
- Complex error message generation and suggestion system
- Parameter validation for resolver functions
- Scripts folder with release automation tools
- Multiple CI/CD workflows (performance, security, docs, release)
- Bandit security scanning and extra development dependencies

### Fixed
- Keyword-only parameters now work properly with @inject decorator
- @inject decorator now works with @classmethod and @staticmethod in any order
- Improved decorator interaction compatibility
- Thread safety issues resolved through explicit scope management

### Security
- Enhanced security through explicit scope boundaries
- Reduced global state vulnerabilities

## [0.1.0] - 2024-01-15

### Added
- Initial release of injectipy
- Thread-safe dependency injection system
- Circular dependency detection
- Type safety with mypy support
- Forward reference support
- Comprehensive test suite (64 tests, 98% coverage)
- Multi-platform CI/CD pipeline
- Security scanning and vulnerability detection
- Performance regression testing
- Documentation and examples
- Pre-commit hooks and code quality tools

### Features
- `@inject` decorator for dependency injection
- `Inject[key]` type-safe parameter markers
- `InjectipyStore` for thread-safe dependency management
- Lazy evaluation with optional caching
- Support for values, resolvers, and callable dependencies
- Context manager support for testing

### Infrastructure
- GitHub Actions CI/CD with Python 3.11 testing
- Ubuntu testing environment
- Automated dependency updates with Dependabot
- Code coverage reporting with 90% threshold

[Unreleased]: https://github.com/Wimonder/injectipy/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Wimonder/injectipy/releases/tag/v0.1.0
