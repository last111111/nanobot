"""Helpers for resolving runtime metadata and placeholders for skills."""

from __future__ import annotations

import sys
from pathlib import Path


SKILL_FILE_NAME = "SKILL.md"


def find_skill_root(path: Path) -> Path | None:
    """Return the nearest parent directory that contains a SKILL.md file."""
    resolved = path.expanduser().resolve()
    candidates = [resolved] if resolved.is_dir() else [resolved.parent]
    candidates.extend(parent for parent in candidates[0].parents)

    for candidate in candidates:
        if (candidate / SKILL_FILE_NAME).is_file():
            return candidate
    return None


def resolve_skill_placeholders(content: str, skill_root: Path | None) -> str:
    """Replace standard skill runtime placeholders in markdown content."""
    if not skill_root:
        return content

    replacements = {
        "{baseDir}": str(skill_root),
        "{skillDir}": str(skill_root),
        "{skillRoot}": str(skill_root),
        "{skillName}": skill_root.name,
        "{pythonExe}": sys.executable,
    }

    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)
    return content
