#!/usr/bin/env python3
"""Automated changelog generation script.

This script generates changelog entries from git commits between releases,
categorizing them by conventional commit types and updating CHANGELOG.md.

Features:
- Parses conventional commits (feat:, fix:, docs:, etc.)
- Categorizes changes by type (Added, Changed, Fixed, etc.)
- Generates links to commits and comparisons
- Updates CHANGELOG.md with new release entries
- Supports custom commit message parsing

Usage:
    python scripts/changelog_generator.py                    # Generate for unreleased changes
    python scripts/changelog_generator.py --release v1.2.0   # Generate release entry
    python scripts/changelog_generator.py --from v1.0.0      # Generate changes since v1.0.0
"""

import argparse
import re
import subprocess  # nosec B404
from datetime import datetime
from pathlib import Path
from typing import Optional


class CommitInfo:
    """Information about a git commit."""

    def __init__(self, hash: str, message: str, author: str, date: str):
        self.hash = hash
        self.message = message
        self.author = author
        self.date = date
        self.type, self.scope, self.description = self._parse_conventional_commit()

    def _parse_conventional_commit(self) -> tuple[str, Optional[str], str]:
        """Parse conventional commit format: type(scope): description."""
        # Conventional commit pattern: type(scope): description
        pattern = r"^([a-z]+)(?:\(([^)]+)\))?: (.+)$"
        match = re.match(pattern, self.message, re.IGNORECASE)

        if match:
            return match.group(1).lower(), match.group(2), match.group(3)

        # Fallback: treat as misc change
        return "misc", None, self.message


class ChangelogGenerator:
    """Generator for automated changelog entries."""

    # Mapping of conventional commit types to changelog categories
    TYPE_MAPPING = {
        "feat": "Added",
        "feature": "Added",
        "add": "Added",
        "fix": "Fixed",
        "bugfix": "Fixed",
        "docs": "Documentation",
        "doc": "Documentation",
        "style": "Changed",
        "refactor": "Changed",
        "perf": "Changed",
        "performance": "Changed",
        "test": "Testing",
        "tests": "Testing",
        "ci": "Infrastructure",
        "cd": "Infrastructure",
        "build": "Infrastructure",
        "chore": "Maintenance",
        "deps": "Dependencies",
        "security": "Security",
        "breaking": "Changed",
        "remove": "Removed",
        "deprecate": "Deprecated",
        "misc": "Changed",
    }

    def __init__(self, repo_url: str = "https://github.com/Wimonder/injectipy"):
        self.repo_url = repo_url
        self.project_root = Path(__file__).parent.parent

    def get_git_commits(self, from_ref: Optional[str] = None, to_ref: str = "HEAD") -> list[CommitInfo]:
        """Get git commits between references."""
        if from_ref:
            commit_range = f"{from_ref}..{to_ref}"
        else:
            # Get commits since last tag
            try:
                last_tag = (
                    subprocess.check_output(  # nosec B603 B607
                        ["git", "describe", "--tags", "--abbrev=0"], cwd=self.project_root, stderr=subprocess.DEVNULL
                    )
                    .decode()
                    .strip()
                )
                commit_range = f"{last_tag}..{to_ref}"
            except subprocess.CalledProcessError:
                # No tags found, get all commits
                commit_range = to_ref

        try:
            # Get commit info in format: hash|subject|author|date
            output = subprocess.check_output(  # nosec B603 B607
                ["git", "log", commit_range, "--pretty=format:%H|%s|%an|%ad", "--date=short", "--reverse"],
                cwd=self.project_root,
            ).decode()

            commits = []
            for line in output.strip().split("\n"):
                if line:
                    parts = line.split("|", 3)
                    if len(parts) == 4:
                        commits.append(CommitInfo(parts[0], parts[1], parts[2], parts[3]))

            return commits

        except subprocess.CalledProcessError as e:
            print(f"Error getting git commits: {e}")
            return []

    def categorize_commits(self, commits: list[CommitInfo]) -> dict[str, list[CommitInfo]]:
        """Categorize commits by changelog section."""
        categories: dict[str, list[CommitInfo]] = {}

        for commit in commits:
            category = self.TYPE_MAPPING.get(commit.type, "Changed")

            if category not in categories:
                categories[category] = []

            categories[category].append(commit)

        return categories

    def format_commit_entry(self, commit: CommitInfo) -> str:
        """Format a single commit as a changelog entry."""
        # Create commit link
        commit_link = f"{self.repo_url}/commit/{commit.hash}"
        short_hash = commit.hash[:7]

        # Format description
        description = commit.description
        if commit.scope:
            description = f"**{commit.scope}**: {description}"

        return f"- {description} ([{short_hash}]({commit_link}))"

    def generate_changelog_section(self, version: str, date: str, commits: list[CommitInfo]) -> str:
        """Generate a complete changelog section for a version."""
        if not commits:
            return ""

        categories = self.categorize_commits(commits)

        # Build changelog section
        lines = [f"## [{version}] - {date}", ""]

        # Order categories by importance
        category_order = [
            "Added",
            "Changed",
            "Deprecated",
            "Removed",
            "Fixed",
            "Security",
            "Documentation",
            "Testing",
            "Infrastructure",
            "Dependencies",
            "Maintenance",
        ]

        for category in category_order:
            if category in categories:
                lines.append(f"### {category}")
                lines.append("")

                for commit in categories[category]:
                    lines.append(self.format_commit_entry(commit))

                lines.append("")

        return "\n".join(lines)

    def update_changelog(self, version: str, changelog_section: str) -> None:
        """Update CHANGELOG.md with new version section."""
        changelog_path = self.project_root / "CHANGELOG.md"

        if not changelog_path.exists():
            print("CHANGELOG.md not found. Creating new one.")
            with open(changelog_path, "w") as f:
                f.write("# Changelog\n\n")
                f.write("All notable changes to this project will be documented in this file.\n\n")
                f.write("The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),\n")
                f.write("and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n\n")

        # Read existing changelog
        with open(changelog_path) as f:
            content = f.read()

        # Find insertion point (after "## [Unreleased]" section)
        unreleased_pattern = r"(## \[Unreleased\].*?)(\n## \[|\nz)"
        match = re.search(unreleased_pattern, content, re.DOTALL)

        if match:
            # Insert new version section after Unreleased
            before = content[: match.end(1)]
            after = content[match.start(2) :]
            new_content = f"{before}\n\n{changelog_section.rstrip()}{after}"
        else:
            # Add at the end if no pattern found
            new_content = f"{content}\n\n{changelog_section}"

        # Update version links at bottom
        version_links = self._generate_version_links(version)
        if version_links:
            new_content = self._update_version_links(new_content, version_links)

        # Write updated changelog
        with open(changelog_path, "w") as f:
            f.write(new_content)

        print(f"✅ Updated CHANGELOG.md with version {version}")

    def _generate_version_links(self, version: str) -> str:
        """Generate version comparison links."""
        try:
            # Get previous tag
            tags_output = subprocess.check_output(  # nosec B603 B607
                ["git", "tag", "-l", "--sort=-version:refname"], cwd=self.project_root
            ).decode()

            tags = [tag.strip() for tag in tags_output.split("\n") if tag.strip()]

            if len(tags) >= 1:
                prev_tag = tags[0] if tags[0] != f"v{version}" else (tags[1] if len(tags) > 1 else None)

                links = []
                links.append(f"[Unreleased]: {self.repo_url}/compare/v{version}...HEAD")

                if prev_tag:
                    links.append(f"[{version}]: {self.repo_url}/compare/{prev_tag}...v{version}")
                else:
                    links.append(f"[{version}]: {self.repo_url}/releases/tag/v{version}")

                return "\n".join(links)

        except subprocess.CalledProcessError:
            pass

        return f"[{version}]: {self.repo_url}/releases/tag/v{version}"

    def _update_version_links(self, content: str, new_links: str) -> str:
        """Update version links section at bottom of changelog."""
        # Find existing links section (usually at the end)
        links_pattern = r"\n\[Unreleased\]:.*$"
        match = re.search(links_pattern, content, re.MULTILINE | re.DOTALL)

        if match:
            # Replace existing links
            return content[: match.start()] + f"\n{new_links}"
        else:
            # Add links section
            return f"{content}\n\n{new_links}"


def main() -> None:
    """Main entry point for changelog generation."""
    parser = argparse.ArgumentParser(description="Generate automated changelog from git commits")
    parser.add_argument("--release", help="Version to generate changelog for (e.g., v1.2.0)")
    parser.add_argument("--from", dest="from_ref", help="Generate changes since this reference")
    parser.add_argument("--to", default="HEAD", help="Generate changes up to this reference")
    parser.add_argument("--dry-run", action="store_true", help="Print changelog without updating file")

    args = parser.parse_args()

    generator = ChangelogGenerator()

    # Get commits
    commits = generator.get_git_commits(args.from_ref, args.to)

    if not commits:
        print("No commits found for changelog generation.")
        return

    print(f"Found {len(commits)} commits to process")

    # Generate changelog section
    if args.release:
        version = args.release.lstrip("v")
        date = datetime.now().strftime("%Y-%m-%d")
    else:
        version = "Unreleased"
        date = ""

    changelog_section = generator.generate_changelog_section(version, date, commits)

    if args.dry_run:
        print("Generated changelog section:")
        print("=" * 50)
        print(changelog_section)
    else:
        if changelog_section.strip():
            generator.update_changelog(version, changelog_section)
        else:
            print("No changes to add to changelog.")


if __name__ == "__main__":
    main()
