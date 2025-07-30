#!/usr/bin/env python3
"""Generate API documentation from source code.

This script automatically generates MkDocs-compatible API documentation
from the injectipy source code using mkdocstrings.
"""

import sys
from pathlib import Path
from typing import Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import mkdocs_gen_files  # noqa: E402

# Package structure to document
API_STRUCTURE = {
    "inject": "injectipy.inject",
    "models": {"inject": "injectipy.models.inject"},
    "store": "injectipy.store",
}


def generate_module_doc(module_path: str, nav_path: str) -> None:
    """Generate documentation for a single module."""
    doc_content = f"""# {nav_path.replace('/', '.')}

::: {module_path}
"""

    with mkdocs_gen_files.open(f"reference/{nav_path}.md", "w") as f:
        f.write(doc_content)


def generate_index() -> None:
    """Generate the API reference index."""
    index_content = """# API Reference

This section contains the complete API reference for injectipy.

## Core Components

- [`inject`](inject.md) - The main dependency injection decorator
- [`Inject`](models/inject.md) - Type-safe dependency marker for dependency injection
- [`InjectipyStore`](store.md) - Thread-safe dependency container and resolver

## Quick Links

- [inject decorator](inject.md#injectipy.inject.inject) - Enable dependency injection on functions
- [Inject class](models/inject.md#injectipy.models.inject.Inject) - Mark dependencies for injection
- [InjectipyStore](store.md#injectipy.store.InjectipyStore) - Main dependency container
- [injectipy_store](store.md#injectipy.store.injectipy_store) - Global singleton instance

## Package Information

- **Version**: {version}
- **Python Support**: 3.9+
- **Type Hints**: Full type safety with mypy support
- **Thread Safety**: All components are thread-safe
"""

    # Get version from package
    try:
        import injectipy

        version = injectipy.__version__
    except ImportError:
        version = "Unknown"

    with mkdocs_gen_files.open("reference/index.md", "w") as f:
        f.write(index_content.format(version=version))


def generate_nav() -> None:
    """Generate the navigation structure."""
    nav_content = """* [API Reference](index.md)
* [inject](inject.md)
* [Models](models/)
    * [Inject](models/inject.md)
* [store](store.md)
"""

    with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as f:
        f.write(nav_content)


def process_structure(structure: dict[str, Any], prefix: str = "") -> None:
    """Recursively process the API structure."""
    for key, value in structure.items():
        if isinstance(value, dict):
            # Create directory and process subdirectories
            process_structure(value, f"{prefix}{key}/")
        else:
            # Generate documentation for module
            nav_path = f"{prefix}{key}"
            generate_module_doc(value, nav_path)


def main() -> None:
    """Generate all API documentation."""
    print("Generating API documentation...")

    # Generate module documentation
    process_structure(API_STRUCTURE)

    # Generate index and navigation
    generate_index()
    generate_nav()

    print("✅ API documentation generated successfully")


if __name__ == "__main__":
    main()
