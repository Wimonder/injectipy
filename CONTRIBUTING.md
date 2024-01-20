# Contributing to Injectipy

Thank you for your interest in contributing to Injectipy! This document provides guidelines and information for contributors.

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/injectipy.git
   cd injectipy
   ```

3. **Set up the development environment**:
   ```bash
   # Install Poetry (if not already installed)
   curl -sSL https://install.python-poetry.org | python3 -

   # Install dependencies
   poetry install

   # Install pre-commit hooks
   poetry run pre-commit install
   ```

4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

5. **Make your changes** and commit them
6. **Push to your fork** and create a pull request

## 🛠️ Development Setup

### Prerequisites

- Python 3.11 or higher
- [Poetry](https://python-poetry.org/) for dependency management
- Git

### Environment Setup

```bash
# Clone the repository
git clone https://github.com/Wimonder/injectipy.git
cd injectipy

# Install Poetry dependencies
poetry install

# Activate the virtual environment
poetry shell

# Install pre-commit hooks
pre-commit install
```

### Development Tools

We use several tools to maintain code quality:

- **Poetry**: Dependency management and packaging
- **Black**: Code formatting
- **Ruff**: Fast Python linting
- **MyPy**: Static type checking
- **pytest**: Testing framework
- **Pre-commit**: Git hooks for code quality

## 🧪 Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=injectipy --cov-report=html

# Run specific test files by functionality
poetry run pytest tests/test_core_inject.py            # Basic @inject decorator tests
poetry run pytest tests/test_scope_functionality.py   # DependencyScope tests
poetry run pytest tests/test_error_handling.py        # Error handling tests
poetry run pytest tests/test_parameter_types.py       # Parameter type support tests
poetry run pytest tests/test_decorator_compatibility.py # Decorator interaction tests
poetry run pytest tests/test_thread_safety.py         # Thread safety tests
poetry run pytest tests/test_performance.py           # Performance benchmarks
poetry run pytest tests/test_python_features.py       # Advanced Python feature tests
```

### Test Categories

We organize tests using pytest markers:

- `performance`: Performance and stress tests
- `edge_case`: Edge cases and error condition tests
- `slow`: Tests that take longer to run
- `integration`: Integration tests

### Test Organization

Tests are organized by functionality in separate files:

- `test_core_inject.py`: Basic @inject decorator functionality
- `test_scope_functionality.py`: DependencyScope registration and resolution
- `test_error_handling.py`: Error cases and exception handling
- `test_parameter_types.py`: Different parameter type support (regular, keyword-only, positional-only)
- `test_decorator_compatibility.py`: Interaction with other Python decorators
- `test_thread_safety.py`: Thread safety and concurrent access tests
- `test_performance.py`: Performance benchmarks and stress tests
- `test_python_features.py`: Advanced Python feature compatibility

### Writing Tests

- Place tests in the appropriate test file based on functionality
- Use descriptive test names: `test_should_inject_dependency_when_registered`
- Follow the AAA pattern: Arrange, Act, Assert
- Use appropriate pytest markers
- Import specific exceptions for error testing: `DependencyNotFoundError`, `CircularDependencyError`, etc.

Example test:

```python
import pytest
from injectipy import DependencyScope, Inject, inject, DependencyNotFoundError

@pytest.fixture
def scope():
    return DependencyScope()

def test_should_inject_registered_value(scope):
    # Arrange
    scope.register_value("test_key", "test_value")

    @inject
    def test_function(value: str = Inject["test_key"]):
        return value

    # Act & Assert
    with scope:
        result = test_function()
        assert result == "test_value"

def test_should_raise_exception_for_missing_dependency(scope):
    # Arrange
    @inject
    def test_function(value: str = Inject["missing_key"]):
        return value

    # Act & Assert
    with scope:
        with pytest.raises(DependencyNotFoundError, match="Dependency 'missing_key' not found"):
            test_function()
```

## 🎨 Code Style

### Formatting and Linting

We enforce consistent code style using automated tools:

```bash
# Format code
poetry run black .

# Lint code
poetry run ruff check .

# Type checking
poetry run mypy injectipy/


# Run all quality checks
poetry run pre-commit run --all-files
```

### Style Guidelines

- Follow PEP 8 and PEP 484 (type hints)
- Use descriptive variable and function names
- Write docstrings for all public functions and classes
- Keep functions small and focused
- Use type hints consistently
- Prefer explicit over implicit

### Docstring Format

Use Google-style docstrings:

```python
def register_value(self, key: str | type, value: object) -> DependencyScope:
    """Register a concrete value in the dependency scope.

    Args:
        key: The key to register the value under
        value: The value to register

    Returns:
        Self for method chaining

    Raises:
        DuplicateRegistrationError: If the key is already registered

    Example:
        >>> scope = DependencyScope()
        >>> scope.register_value("config", {"debug": True})
    """
```

## 🏗️ Architecture

### Core Components

- **DependencyScope**: Context-managed dependency registry
- **@inject decorator**: Function/method injection decorator
- **Inject[key]**: Dependency marker for injection
- **Thread Safety**: All operations are thread-safe

### Design Principles

- **Simplicity**: Keep the API minimal and intuitive
- **Performance**: Optimize for common use cases
- **Thread Safety**: All operations must be thread-safe
- **Type Safety**: Full type hint support
- **Testability**: Design for easy testing

## 📋 Contribution Guidelines

### Before Contributing

1. **Check existing issues** to avoid duplicates
2. **Discuss large changes** by opening an issue first
3. **Read the documentation** to understand current behavior
4. **Review recent PRs** to understand conventions

### Pull Request Process

1. **Create an issue** for significant changes
2. **Fork and clone** the repository
3. **Create a feature branch** from `main`
4. **Make your changes** with tests
5. **Run the test suite** and ensure all tests pass
6. **Update documentation** if needed
7. **Submit a pull request** with a clear description

### Pull Request Requirements

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated if necessary
- [ ] Changelog entry added for user-facing changes
- [ ] PR description clearly explains the change

### Commit Message Format

Use conventional commit format:

```
type(scope): description

[Optional body explaining the change]

[Optional footer with breaking changes or issue references]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build/CI changes

Examples:
```
feat(store): add circular dependency detection
fix(inject): handle missing dependencies gracefully
docs(readme): update installation instructions
```

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Clear description** of the issue
2. **Minimal reproducible example**
3. **Expected vs actual behavior**
4. **Environment information** (Python version, OS, etc.)
5. **Error messages** and stack traces

Use our bug report template when creating issues.

## ✨ Feature Requests

For feature requests, please:

1. **Describe the problem** you're trying to solve
2. **Explain your proposed solution**
3. **Provide API examples** showing how it would work
4. **Consider alternatives** and explain why your approach is best
5. **Indicate willingness** to help implement

## 🔒 Security

If you discover a security vulnerability:

1. **Do not** open a public issue
2. **Email the maintainer** directly
3. **Provide details** about the vulnerability
4. **Allow time** for the issue to be addressed before disclosure

## 📄 License

By contributing to Injectipy, you agree that your contributions will be licensed under the MIT License.

## 🤝 Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Expected Behavior

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information without permission
- Other conduct which could reasonably be considered inappropriate

## 🙋 Getting Help

- **Documentation**: Check the README and API documentation
- **Issues**: Search existing issues or create a new one
- **Discussions**: Use GitHub Discussions for questions
- **Examples**: Check the `examples/` directory

## 🎯 Areas for Contribution

We welcome contributions in these areas:

### High Priority
- Bug fixes and stability improvements
- Performance optimizations
- Documentation improvements

### Medium Priority
- New features (after discussion)
- Framework integrations
- Development tooling improvements
- Example applications

### Low Priority
- Code refactoring
- Style improvements
- Minor feature enhancements

## 📈 Development Workflow

1. **Issue Discussion**: Discuss significant changes in an issue first
2. **Implementation**: Implement changes with tests
3. **Code Review**: Submit PR for review
4. **Integration**: Merge after approval and CI passing
5. **Release**: Changes included in next release

## 🏆 Recognition

Contributors will be:
- Listed in the CONTRIBUTORS file
- Mentioned in release notes for significant contributions
- Invited to join the maintainer team for ongoing contributors

Thank you for contributing to Injectipy! 🎉
