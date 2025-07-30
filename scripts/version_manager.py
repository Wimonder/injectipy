#!/usr/bin/env python3
"""Version management script for semantic versioning.

This script helps manage semantic versioning (MAJOR.MINOR.PATCH) according to:
- MAJOR: Incompatible API changes
- MINOR: Backwards-compatible functionality additions
- PATCH: Backwards-compatible bug fixes

Usage:
    python scripts/version_manager.py patch    # Bump patch version (0.1.0 -> 0.1.1)
    python scripts/version_manager.py minor    # Bump minor version (0.1.0 -> 0.2.0)
    python scripts/version_manager.py major    # Bump major version (0.1.0 -> 1.0.0)
    python scripts/version_manager.py current  # Show current version
"""

import re
import sys
import toml
from pathlib import Path
from typing import Tuple


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_current_version() -> Tuple[str, str, str]:
    """Get current version from pyproject.toml and __init__.py."""
    project_root = get_project_root()
    
    # Read from pyproject.toml
    pyproject_path = project_root / "pyproject.toml"
    with open(pyproject_path, "r") as f:
        pyproject_data = toml.load(f)
    
    pyproject_version = pyproject_data["tool"]["poetry"]["version"]
    
    # Read from __init__.py
    init_path = project_root / "injectipy" / "__init__.py"
    with open(init_path, "r") as f:
        init_content = f.read()
    
    version_match = re.search(r'__version__ = ["\']([^"\']+)["\']', init_content)
    if not version_match:
        raise ValueError("Could not find __version__ in __init__.py")
    
    init_version = version_match.group(1)
    
    if pyproject_version != init_version:
        raise ValueError(f"Version mismatch: pyproject.toml has {pyproject_version}, __init__.py has {init_version}")
    
    return pyproject_version, pyproject_path, init_path


def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse semantic version string into major, minor, patch tuple."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version)
    if not match:
        raise ValueError(f"Invalid semantic version: {version}")
    
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def format_version(major: int, minor: int, patch: int) -> str:
    """Format version tuple into semantic version string."""
    return f"{major}.{minor}.{patch}"


def bump_version(version: str, bump_type: str) -> str:
    """Bump version according to semantic versioning rules."""
    major, minor, patch = parse_version(version)
    
    if bump_type == "major":
        return format_version(major + 1, 0, 0)
    elif bump_type == "minor":
        return format_version(major, minor + 1, 0)
    elif bump_type == "patch":
        return format_version(major, minor, patch + 1)
    else:
        raise ValueError(f"Invalid bump type: {bump_type}. Use 'major', 'minor', or 'patch'")


def update_pyproject_toml(path: Path, new_version: str) -> None:
    """Update version in pyproject.toml."""
    with open(path, "r") as f:
        content = f.read()
    
    # Update version using regex to preserve formatting
    updated_content = re.sub(
        r'(version = ["\'])([^"\']+)(["\'])',
        f'\\g<1>{new_version}\\g<3>',
        content
    )
    
    with open(path, "w") as f:
        f.write(updated_content)


def update_init_py(path: Path, new_version: str) -> None:
    """Update version in __init__.py."""
    with open(path, "r") as f:
        content = f.read()
    
    # Update version using regex to preserve formatting
    updated_content = re.sub(
        r'(__version__ = ["\'])([^"\']+)(["\'])',
        f'\\g<1>{new_version}\\g<3>',
        content
    )
    
    with open(path, "w") as f:
        f.write(updated_content)


def main():
    """Main entry point for version management."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/version_manager.py <major|minor|patch|current>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        current_version, pyproject_path, init_path = get_current_version()
        print(f"Current version: {current_version}")
        
        if command == "current":
            return
        
        if command not in ["major", "minor", "patch"]:
            print(f"Invalid command: {command}. Use 'major', 'minor', 'patch', or 'current'")
            sys.exit(1)
        
        new_version = bump_version(current_version, command)
        print(f"Bumping {command} version: {current_version} -> {new_version}")
        
        # Update both files
        update_pyproject_toml(Path(pyproject_path), new_version)
        update_init_py(Path(init_path), new_version)
        
        print(f"✅ Version updated to {new_version}")
        print("📝 Remember to:")
        print("   1. Update CHANGELOG.md with release notes")
        print("   2. Commit changes and create a git tag")
        print(f"   3. Run: git tag v{new_version}")
        print("   4. Push tags: git push --tags")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()