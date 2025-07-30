# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Semantic versioning implementation
- Automated changelog generation
- Release management automation

### Changed

### Deprecated

### Removed

### Fixed

### Security

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
- GitHub Actions CI/CD with multi-Python version testing (3.9-3.12)
- Multi-OS testing (Linux, macOS, Windows)
- Automated dependency updates with Dependabot
- Code coverage reporting with 90% threshold
- Performance benchmarking and regression detection
- Security vulnerability scanning
- Automated release pipeline

[Unreleased]: https://github.com/Wimonder/injectipy/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Wimonder/injectipy/releases/tag/v0.1.0
