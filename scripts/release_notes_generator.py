#!/usr/bin/env python3
"""Release notes generation script.

This script generates comprehensive release notes from changelog entries,
commit history, and project metadata for GitHub releases and documentation.

Features:
- Extracts release information from CHANGELOG.md
- Generates GitHub-flavored markdown release notes
- Includes download links and installation instructions
- Categorizes changes with emojis and formatting
- Supports custom templates and formatting

Usage:
    python scripts/release_notes_generator.py v1.2.0              # Generate release notes for v1.2.0
    python scripts/release_notes_generator.py --latest            # Generate for latest version
    python scripts/release_notes_generator.py --template custom   # Use custom template
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class ReleaseNotesGenerator:
    """Generator for automated release notes."""
    
    # Emoji mapping for different change categories
    CATEGORY_EMOJIS = {
        'Added': '✨',
        'Changed': '🔄', 
        'Deprecated': '⚠️',
        'Removed': '🗑️',
        'Fixed': '🐛',
        'Security': '🔒',
        'Documentation': '📚',
        'Testing': '🧪',
        'Infrastructure': '🏗️',
        'Dependencies': '📦',
        'Maintenance': '🔧',
        'Performance': '⚡'
    }
    
    def __init__(self, repo_url: str = "https://github.com/Wimonder/injectipy"):
        self.repo_url = repo_url
        self.project_root = Path(__file__).parent.parent
    
    def extract_version_changelog(self, version: str) -> Optional[Dict[str, any]]:
        """Extract changelog section for a specific version."""
        changelog_path = self.project_root / "CHANGELOG.md"
        
        if not changelog_path.exists():
            print("CHANGELOG.md not found")
            return None
        
        with open(changelog_path, 'r') as f:
            content = f.read()
        
        # Pattern to match version section
        version_pattern = rf'## \[{re.escape(version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})(.*?)(?=\n## \[|\n\[.*?\]:|$)'
        match = re.search(version_pattern, content, re.DOTALL)
        
        if not match:
            print(f"Version {version} not found in CHANGELOG.md")
            return None
        
        date = match.group(1)
        changelog_content = match.group(2).strip()
        
        # Parse sections
        sections = self._parse_changelog_sections(changelog_content)
        
        return {
            'version': version,
            'date': date,
            'sections': sections,
            'raw_content': changelog_content
        }
    
    def _parse_changelog_sections(self, content: str) -> Dict[str, List[str]]:
        """Parse changelog content into categorized sections."""
        sections = {}
        current_section = None
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a section header (### Category)
            if line.startswith('### '):
                current_section = line[4:].strip()
                sections[current_section] = []
            elif line.startswith('- ') and current_section:
                # Remove leading dash and clean up
                item = line[2:].strip()
                sections[current_section].append(item)
        
        return sections
    
    def get_latest_version(self) -> Optional[str]:
        """Get the latest version from CHANGELOG.md."""
        changelog_path = self.project_root / "CHANGELOG.md"
        
        if not changelog_path.exists():
            return None
        
        with open(changelog_path, 'r') as f:
            content = f.read()
        
        # Find first version section (after Unreleased)
        pattern = r'## \[(\d+\.\d+\.\d+)\]'
        match = re.search(pattern, content)
        
        return match.group(1) if match else None
    
    def generate_release_notes(self, version_info: Dict[str, any], template: str = "default") -> str:
        """Generate formatted release notes from version information."""
        if template == "github":
            return self._generate_github_release_notes(version_info)
        elif template == "detailed":
            return self._generate_detailed_release_notes(version_info)
        else:
            return self._generate_default_release_notes(version_info)
    
    def _generate_default_release_notes(self, version_info: Dict[str, any]) -> str:
        """Generate default format release notes."""
        version = version_info['version']
        date = version_info['date']
        sections = version_info['sections']
        
        lines = [
            f"# Release {version}",
            "",
            f"**Release Date:** {date}",
            "",
            "## What's New",
            ""
        ]
        
        # Add sections with emojis
        for category, items in sections.items():
            if not items:
                continue
            
            emoji = self.CATEGORY_EMOJIS.get(category, '📝')
            lines.append(f"### {emoji} {category}")
            lines.append("")
            
            for item in items:
                lines.append(f"- {item}")
            
            lines.append("")
        
        # Add installation instructions
        lines.extend([
            "## Installation",
            "",
            "```bash",
            f"pip install injectipy=={version}",
            "```",
            "",
            "## Documentation",
            "",
            f"- [Documentation]({self.repo_url})",
            f"- [API Reference]({self.repo_url}#api-reference)",
            f"- [Examples]({self.repo_url}/tree/main/examples)",
            "",
            "## Links",
            "",
            f"- [Full Changelog]({self.repo_url}/blob/main/CHANGELOG.md)",
            f"- [Release Assets]({self.repo_url}/releases/tag/v{version})",
            f"- [PyPI Package](https://pypi.org/project/injectipy/{version}/)",
            ""
        ])
        
        return '\n'.join(lines)
    
    def _generate_github_release_notes(self, version_info: Dict[str, any]) -> str:
        """Generate GitHub release format notes."""
        version = version_info['version']
        sections = version_info['sections']
        
        lines = []
        
        # Add sections in priority order
        priority_order = ['Added', 'Changed', 'Fixed', 'Security', 'Deprecated', 'Removed']
        
        for category in priority_order:
            if category in sections and sections[category]:
                emoji = self.CATEGORY_EMOJIS.get(category, '📝')
                lines.append(f"## {emoji} {category}")
                lines.append("")
                
                for item in sections[category]:
                    lines.append(f"- {item}")
                
                lines.append("")
        
        # Add other categories
        for category, items in sections.items():
            if category not in priority_order and items:
                emoji = self.CATEGORY_EMOJIS.get(category, '📝')
                lines.append(f"## {emoji} {category}")
                lines.append("")
                
                for item in items:
                    lines.append(f"- {item}")
                
                lines.append("")
        
        # Add footer
        lines.extend([
            "---",
            "",
            "**Installation:**",
            "```bash",
            f"pip install injectipy=={version}",
            "```",
            "",
            f"**Full Changelog:** {self.repo_url}/blob/main/CHANGELOG.md"
        ])
        
        return '\n'.join(lines)
    
    def _generate_detailed_release_notes(self, version_info: Dict[str, any]) -> str:
        """Generate detailed release notes with additional context."""
        version = version_info['version']
        date = version_info['date']
        sections = version_info['sections']
        
        lines = [
            f"# Injectipy {version} Release Notes",
            "",
            f"Released on {date}",
            "",
            "## Overview",
            "",
            f"This release includes {sum(len(items) for items in sections.values())} changes across {len(sections)} categories.",
            ""
        ]
        
        # Add highlighted changes
        important_categories = ['Added', 'Changed', 'Security', 'Fixed']
        important_changes = []
        
        for category in important_categories:
            if category in sections:
                important_changes.extend(sections[category])
        
        if important_changes:
            lines.extend([
                "## Highlights",
                "",
            ])
            
            for change in important_changes[:5]:  # Top 5 changes
                lines.append(f"- {change}")
            
            lines.append("")
        
        # Add all sections
        for category, items in sections.items():
            if not items:
                continue
            
            emoji = self.CATEGORY_EMOJIS.get(category, '📝')
            lines.append(f"## {emoji} {category}")
            lines.append("")
            
            for item in items:
                lines.append(f"- {item}")
            
            lines.append("")
        
        # Add upgrade notes if there are breaking changes
        if 'Changed' in sections or 'Deprecated' in sections or 'Removed' in sections:
            lines.extend([
                "## Upgrade Notes",
                "",
                "Please review the changes above, particularly in the **Changed**, **Deprecated**, and **Removed** sections.",
                "Update your code accordingly before upgrading.",
                ""
            ])
        
        # Add installation and resources
        lines.extend([
            "## Installation & Resources",
            "",
            "### Installation",
            "```bash",
            f"pip install injectipy=={version}",
            "```",
            "",
            "### Documentation & Examples",
            f"- [Project Documentation]({self.repo_url})",
            f"- [API Reference]({self.repo_url}#api-reference)", 
            f"- [Usage Examples]({self.repo_url}/tree/main/examples)",
            "",
            "### Support",
            f"- [Issue Tracker]({self.repo_url}/issues)",
            f"- [Discussions]({self.repo_url}/discussions)",
            "",
            f"**Full Changelog:** [CHANGELOG.md]({self.repo_url}/blob/main/CHANGELOG.md)"
        ])
        
        return '\n'.join(lines)
    
    def save_release_notes(self, version: str, content: str, template: str = "default") -> Path:
        """Save release notes to file."""
        # Create releases directory if it doesn't exist
        releases_dir = self.project_root / "releases"
        releases_dir.mkdir(exist_ok=True)
        
        # Generate filename
        filename = f"release-notes-{version}-{template}.md"
        filepath = releases_dir / filename
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        return filepath


def main():
    """Main entry point for release notes generation."""
    parser = argparse.ArgumentParser(description="Generate release notes from changelog")
    parser.add_argument("version", nargs="?", help="Version to generate release notes for (e.g., 1.2.0)")
    parser.add_argument("--latest", action="store_true", help="Generate for latest version")
    parser.add_argument("--template", choices=["default", "github", "detailed"], 
                       default="default", help="Template format for release notes")
    parser.add_argument("--output", help="Output file path (default: releases/release-notes-{version}-{template}.md)")
    parser.add_argument("--print", action="store_true", help="Print to stdout instead of saving to file")
    
    args = parser.parse_args()
    
    generator = ReleaseNotesGenerator()
    
    # Determine version
    if args.latest:
        version = generator.get_latest_version()
        if not version:
            print("No version found in CHANGELOG.md")
            sys.exit(1)
    elif args.version:
        version = args.version.lstrip('v')
    else:
        print("Please specify a version or use --latest")
        sys.exit(1)
    
    print(f"Generating release notes for version {version}")
    
    # Extract changelog information
    version_info = generator.extract_version_changelog(version)
    if not version_info:
        sys.exit(1)
    
    # Generate release notes
    release_notes = generator.generate_release_notes(version_info, args.template)
    
    if args.print:
        print(release_notes)
    else:
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(release_notes)
            print(f"✅ Release notes saved to {output_path}")
        else:
            output_path = generator.save_release_notes(version, release_notes, args.template)
            print(f"✅ Release notes saved to {output_path}")


if __name__ == "__main__":
    main()