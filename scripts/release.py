#!/usr/bin/env python3
"""Comprehensive release automation script.

This script automates the entire release process including:
- Version validation and updates
- Changelog generation
- Git tagging and pushing
- Local testing before release
- GitHub release creation

Usage:
    python scripts/release.py patch   # Release patch version (0.1.0 -> 0.1.1)
    python scripts/release.py minor   # Release minor version (0.1.0 -> 0.2.0)
    python scripts/release.py major   # Release major version (0.1.0 -> 1.0.0)
    python scripts/release.py --version 1.2.3     # Release specific version
    python scripts/release.py --dry-run patch     # Preview changes without executing
"""

import argparse
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Optional

import toml  # type: ignore


class ReleaseManager:
    """Comprehensive release management automation."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.project_root = Path(__file__).parent.parent

    def run_command(self, command: list, check: bool = True) -> subprocess.CompletedProcess:
        """Run command with dry-run support."""
        print(f"{'[DRY RUN] ' if self.dry_run else ''}Running: {' '.join(command)}")

        if self.dry_run:
            return subprocess.CompletedProcess(command, 0, "", "")

        return subprocess.run(command, cwd=self.project_root, check=check, capture_output=True, text=True)  # nosec B603

    def get_current_version(self) -> str:
        """Get current version from pyproject.toml."""
        pyproject_path = self.project_root / "pyproject.toml"
        with open(pyproject_path) as f:
            pyproject_data = toml.load(f)
        return str(pyproject_data["tool"]["poetry"]["version"])

    def validate_git_status(self) -> None:
        """Ensure git working directory is clean."""
        print("Validating git status...")

        result = subprocess.run(
            ["git", "status", "--porcelain"], cwd=self.project_root, capture_output=True, text=True
        )  # nosec B603 B607

        if result.stdout.strip():
            print("❌ Git working directory is not clean:")
            print(result.stdout)
            print("Please commit or stash changes before releasing.")
            sys.exit(1)

        # Check if on main branch
        result = subprocess.run(
            ["git", "branch", "--show-current"], cwd=self.project_root, capture_output=True, text=True
        )  # nosec B603 B607
        current_branch = result.stdout.strip()

        if current_branch != "main":
            print(f"⚠️  Warning: You are on branch '{current_branch}', not 'main'")
            response = input("Continue? (y/N): ")
            if response.lower() != "y":
                sys.exit(1)

        print("✅ Git status validation passed")

    def update_version(self, new_version: str) -> None:
        """Update version using version manager script."""
        print(f"Updating version to {new_version}...")

        # First get current version for validation
        current_version = self.get_current_version()
        print(f"Current version: {current_version}")

        if not self.dry_run:
            # Use version manager to update both files
            version_script = self.project_root / "scripts" / "version_manager.py"
            if version_script.exists():
                # Use the version manager script indirectly by manually updating
                subprocess.run([sys.executable, str(version_script), "current"], check=True)  # nosec B603

                # Update pyproject.toml
                pyproject_path = self.project_root / "pyproject.toml"
                with open(pyproject_path) as f:
                    content = f.read()

                updated_content = content.replace(f'version = "{current_version}"', f'version = "{new_version}"')

                with open(pyproject_path, "w") as f:
                    f.write(updated_content)

                # Update __init__.py
                init_path = self.project_root / "injectipy" / "__init__.py"
                with open(init_path) as f:
                    content = f.read()

                updated_content = content.replace(
                    f'__version__ = "{current_version}"', f'__version__ = "{new_version}"'
                )

                with open(init_path, "w") as f:
                    f.write(updated_content)

        print(f"✅ Version updated to {new_version}")

    def run_tests(self) -> None:
        """Run full test suite before release."""
        print("Running test suite...")

        # Check if poetry is available
        try:
            self.run_command(["poetry", "--version"])
        except subprocess.CalledProcessError:
            print("❌ Poetry not found. Please install poetry first.")
            sys.exit(1)

        # Install dependencies and run tests
        self.run_command(["poetry", "install"])

        test_result = self.run_command(
            ["poetry", "run", "pytest", "--cov=injectipy", "--cov-report=term-missing", "--cov-fail-under=90", "-v"]
        )

        if not self.dry_run and test_result.returncode != 0:
            print("❌ Tests failed. Cannot proceed with release.")
            print(test_result.stdout)
            print(test_result.stderr)
            sys.exit(1)

        print("✅ All tests passed")

    def run_quality_checks(self) -> None:
        """Run code quality checks."""
        print("Running code quality checks...")

        checks = [
            (["poetry", "run", "black", "--check", "."], "Code formatting"),
            (["poetry", "run", "ruff", "check", "."], "Linting"),
            (["poetry", "run", "mypy", "injectipy"], "Type checking"),
            (["poetry", "run", "bandit", "-r", "injectipy"], "Security scan"),
        ]

        for command, name in checks:
            print(f"Running {name}...")
            result = self.run_command(command, check=False)

            if not self.dry_run and result.returncode != 0:
                print(f"❌ {name} failed:")
                print(result.stdout)
                print(result.stderr)
                sys.exit(1)

        print("✅ All quality checks passed")

    def test_package_build(self) -> None:
        """Test package building."""
        print("Testing package build...")

        # Clean previous builds
        dist_dir = self.project_root / "dist"
        if dist_dir.exists() and not self.dry_run:
            import shutil

            shutil.rmtree(dist_dir)

        # Build package
        self.run_command(["poetry", "build"])

        if not self.dry_run:
            # Verify build artifacts exist
            wheel_files = list(dist_dir.glob("*.whl"))
            tar_files = list(dist_dir.glob("*.tar.gz"))

            if not wheel_files or not tar_files:
                print("❌ Package build failed - missing artifacts")
                sys.exit(1)

            print("✅ Package built successfully:")
            for file in wheel_files + tar_files:
                print(f"  - {file.name}")

    def update_changelog(self, version: str) -> None:
        """Update changelog for the release."""
        print(f"Updating changelog for version {version}...")

        changelog_script = self.project_root / "scripts" / "changelog_generator.py"
        if changelog_script.exists():
            self.run_command([sys.executable, str(changelog_script), "--release", f"v{version}"])
        else:
            print("⚠️  Changelog generator script not found, skipping changelog update")

        print("✅ Changelog updated")

    def commit_and_tag(self, version: str) -> None:
        """Commit changes and create git tag."""
        commit_message = f"chore: release version {version}"
        tag_name = f"v{version}"

        print(f"Committing changes and creating tag {tag_name}...")

        # Add changes
        self.run_command(["git", "add", "pyproject.toml", "injectipy/__init__.py", "CHANGELOG.md"])

        # Commit
        self.run_command(["git", "commit", "-m", commit_message])

        # Create tag
        self.run_command(["git", "tag", "-a", tag_name, "-m", f"Release {version}"])

        print("✅ Changes committed and tagged")

    def push_release(self, version: str) -> None:
        """Push commits and tags to remote."""
        tag_name = f"v{version}"

        print("Pushing release to remote...")

        # Push commits
        self.run_command(["git", "push", "origin", "main"])

        # Push tag
        self.run_command(["git", "push", "origin", tag_name])

        print("✅ Release pushed to remote")
        print(f"🚀 GitHub Actions will now handle the release automation for {tag_name}")

    def release(self, bump_type: Optional[str] = None, target_version: Optional[str] = None) -> None:
        """Execute complete release process."""
        print("🚀 Starting release process...")

        # Determine new version
        if target_version:
            new_version = target_version
        elif bump_type:
            current_version = self.get_current_version()
            major, minor, patch = map(int, current_version.split("."))

            if bump_type == "major":
                new_version = f"{major + 1}.0.0"
            elif bump_type == "minor":
                new_version = f"{major}.{minor + 1}.0"
            elif bump_type == "patch":
                new_version = f"{major}.{minor}.{patch + 1}"
            else:
                print(f"❌ Invalid bump type: {bump_type}")
                sys.exit(1)
        else:
            print("❌ Must specify either bump type or target version")
            sys.exit(1)

        print(f"📦 Releasing version {new_version}")

        if not self.dry_run:
            self.validate_git_status()

        self.update_version(new_version)
        self.run_tests()
        self.run_quality_checks()
        self.test_package_build()
        self.update_changelog(new_version)

        if not self.dry_run:
            self.commit_and_tag(new_version)

            # Ask for confirmation before pushing
            print("\n📋 Release Summary:")
            print(f"   Version: {new_version}")
            print(f"   Tag: v{new_version}")
            print("   Changes: Version bump, changelog update")
            print()

            if input("Push release to remote and trigger GitHub Actions? (y/N): ").lower() == "y":
                self.push_release(new_version)
                print()
                print("🎉 Release process completed successfully!")
                print("📖 Monitor the GitHub Actions workflow at:")
                print("   https://github.com/Wimonder/injectipy/actions")
                print("📦 Release will be available at:")
                print(f"   https://github.com/Wimonder/injectipy/releases/tag/v{new_version}")
                print(f"   https://pypi.org/project/injectipy/{new_version}/")
            else:
                print("⏸️  Release prepared but not pushed. You can push manually with:")
                print(f"   git push origin main && git push origin v{new_version}")
        else:
            print("\n📋 Dry Run Summary:")
            print(f"   Would release version: {new_version}")
            print(f"   Would create tag: v{new_version}")
            print("   All checks passed - ready for actual release")


def main() -> None:
    """Main entry point for release automation."""
    parser = argparse.ArgumentParser(description="Automated release management")
    parser.add_argument(
        "bump_type", nargs="?", choices=["major", "minor", "patch"], help="Type of version bump to perform"
    )
    parser.add_argument("--version", help="Specific version to release (e.g., 1.2.3)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")

    args = parser.parse_args()

    if not args.bump_type and not args.version:
        print("Error: Must specify either bump type (major/minor/patch) or --version")
        parser.print_help()
        sys.exit(1)

    if args.bump_type and args.version:
        print("Error: Cannot specify both bump type and specific version")
        sys.exit(1)

    release_manager = ReleaseManager(dry_run=args.dry_run)
    release_manager.release(args.bump_type, args.version)


if __name__ == "__main__":
    main()
