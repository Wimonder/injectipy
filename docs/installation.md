# Installation

## Requirements

- Python 3.11 or higher

## Install from PyPI

The recommended way to install injectipy is from PyPI using pip:

```bash
pip install injectipy
```

### With Poetry

If you're using Poetry for dependency management:

```bash
poetry add injectipy
```

### With pipenv

If you're using pipenv:

```bash
pipenv install injectipy
```

## Development Installation

If you want to contribute to injectipy or install from source:

### 1. Clone the Repository

```bash
git clone https://github.com/Wimonder/injectipy.git
cd injectipy
```

### 2. Install with Poetry (Recommended)

```bash
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate the virtual environment
poetry shell
```

### 3. Install with pip (Alternative)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install pytest pytest-cov black mypy ruff pre-commit
```

## Verify Installation

Test that injectipy is installed correctly:

```python
import injectipy
print(injectipy.__version__)

# Test basic functionality
from injectipy import inject, Inject, DependencyScope

scope = DependencyScope()
scope.register_value("test", "Hello, World!")

@inject
def test_function(message: str = Inject["test"]):
    return message

with scope:
    result = test_function()
    print(result)  # Should print: Hello, World!
```

## Optional Dependencies

For development and testing:

```bash
# Code formatting and linting
pip install black ruff mypy

# Testing
pip install pytest pytest-cov

# Pre-commit hooks
pip install pre-commit
```

## IDE Setup

### VS Code

For the best development experience with VS Code:

1. Install the Python extension
2. Configure Python interpreter to use your virtual environment
3. Add these settings to `.vscode/settings.json`:

```json
{
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.mypyEnabled": true,
    "python.linting.ruffEnabled": true
}
```

### PyCharm

1. Configure Python interpreter to use your virtual environment
2. Enable type checking: Settings → Editor → Inspections → Python → Type checker
3. Configure code style to use Black formatting

## Troubleshooting

### Import Errors

If you encounter import errors:

```python
# Make sure injectipy is properly installed
pip show injectipy

# Check Python path
import sys
print(sys.path)
```

### Version Conflicts

If you have dependency conflicts:

```bash
# Check for conflicts
pip check

# Create a fresh virtual environment
python -m venv fresh_env
source fresh_env/bin/activate
pip install injectipy
```

### Performance Issues

For optimal performance:

- Use Python 3.11+ for best performance
- Enable caching for expensive resolvers
- Consider using `register_value` for static dependencies

## Next Steps

See the main README.md for usage examples and API documentation.
