# Contributing to Injectipy

Thank you for your interest in contributing to injectipy! This guide will help you get started with contributing to the project.

## Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/your-username/injectipy.git
cd injectipy

# Add upstream remote
git remote add upstream https://github.com/Wimonder/injectipy.git
```

### 2. Development Setup

```bash
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Install pre-commit hooks
poetry run pre-commit install

# Activate virtual environment
poetry shell
```

### 3. Run Tests

```bash
# Run the full test suite
poetry run pytest

# Run with coverage
poetry run pytest --cov=injectipy --cov-report=html

# Run specific test files
poetry run pytest tests/test_core_inject.py

# Run performance tests
poetry run pytest -m performance
```

## Development Workflow

### 1. Create a Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write clean, readable code
- Follow existing code style and conventions
- Add tests for new functionality
- Update documentation as needed

### 3. Code Quality

Before committing, ensure your code passes all quality checks:

```bash
# Format code
poetry run black .

# Lint code
poetry run ruff check .

# Type checking
poetry run mypy injectipy

# Run all tests
poetry run pytest
```

### 4. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add new dependency resolution feature"

# Push to your fork
git push origin feature/your-feature-name
```

### 5. Create Pull Request

1. Go to GitHub and create a pull request from your fork
2. Fill out the pull request template
3. Wait for review and address feedback

## Contribution Guidelines

### Code Style

- **Formatting**: Use Black for code formatting (120 char line length)
- **Linting**: Code must pass Ruff linting checks
- **Type Hints**: All public functions must have type hints
- **Docstrings**: Use Google-style docstrings for all public functions

Example:

```python
def register_resolver(
    self,
    key: str | type,
    resolver: Callable[..., object],
    *,
    evaluate_once: bool = False
) -> DependencyScope:
    """Register a resolver function for dependency injection.

    Args:
        key: The dependency key to register
        resolver: Function that creates the dependency instance
        evaluate_once: Whether to cache the resolved instance

    Returns:
        Self for method chaining

    Raises:
        DuplicateRegistrationError: If key is already registered
        CircularDependencyError: If circular dependency detected

    Example:
        >>> scope.register_resolver("service", lambda: MyService())
        >>> scope.register_resolver("db", create_db_connection, evaluate_once=True)
    """
```

### Testing

- **Test Types**: Write unit tests, integration tests, and performance tests
- **Test Organization**: Use clear test names and organize by functionality
- **Mocking**: Use appropriate mocking for external dependencies

Example test:

```python
def test_register_resolver_with_evaluate_once():
    """Test that resolver evaluate_once works correctly."""
    scope = DependencyScope()
    call_count = 0

    def expensive_resolver():
        nonlocal call_count
        call_count += 1
        return f"result_{call_count}"

    scope.register_resolver("cached", expensive_resolver, evaluate_once=True)

    with scope:
        # First call should execute resolver
        result1 = scope["cached"]
        assert result1 == "result_1"
        assert call_count == 1

        # Second call should use cached value
        result2 = scope["cached"]
        assert result2 == "result_1"  # Same result
        assert call_count == 1  # Resolver not called again
```

### Documentation

- **API Docs**: All public functions need docstrings
- **User Docs**: Update user documentation for new features
- **Examples**: Include practical examples in docstrings and docs
- **Changelog**: Add entries to CHANGELOG.md for user-facing changes

### Commit Messages

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code formatting changes
- `refactor`: Code changes that don't add features or fix bugs
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(store): add support for scoped dependencies
fix(inject): resolve circular dependency detection issue
docs: update advanced patterns guide
test: add performance benchmarks for large dependency graphs
```

## Areas for Contribution

### 🐛 Bug Fixes
- Check the [issue tracker](https://github.com/Wimonder/injectipy/issues) for bugs
- Look for issues labeled `bug` or `help wanted`

### ✨ New Features
- Dependency scoping (request, session, etc.)
- Framework integrations (FastAPI, Flask, Django)
- Performance optimizations
- Additional resolver types

### 📚 Documentation
- Improve existing documentation
- Add more examples and tutorials
- Create video tutorials or blog posts
- Improve API documentation

### 🧪 Testing
- Add more edge case tests
- Improve performance benchmarks
- Add integration tests
- Test on different Python versions

### 🏗️ Infrastructure
- Improve CI/CD pipelines
- Add security scanning
- Optimize build processes
- Improve development tooling

## Release Process

Releases are automated through GitHub Actions:

1. **Version Bump**: Use Poetry to bump version
   ```bash
   poetry version patch  # or minor/major
   ```

2. **Update Changelog**: Add release notes to CHANGELOG.md

3. **Create Release**: Push tag to trigger release workflow
   ```bash
   git tag v1.2.3
   git push origin v1.2.3
   ```

## Getting Help

- 💬 [GitHub Discussions](https://github.com/Wimonder/injectipy/discussions)
- 🐛 [Issue Tracker](https://github.com/Wimonder/injectipy/issues)
- 📖 [Documentation](https://wimonder.github.io/injectipy/)

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/). Please be respectful and inclusive in all interactions.

## Recognition

Contributors are recognized in:
- GitHub contributors list
- Release notes for significant contributions
- Documentation acknowledgments

Thank you for contributing to injectipy! 🎉
