"""Skills loader for agent capabilities."""

import importlib.util
import json
import os
import platform
import re
import shutil
from pathlib import Path

from loguru import logger

from nanobot.utils.skill_runtime import resolve_skill_placeholders

# Default builtin skills directory (relative to this file)
BUILTIN_SKILLS_DIR = Path(__file__).parent.parent / "skills"


class SkillsLoader:
    """
    Loader for agent skills.
    
    Skills are markdown files (SKILL.md) that teach the agent how to use
    specific tools or perform certain tasks.
    """
    
    def __init__(self, workspace: Path, builtin_skills_dir: Path | None = None):
        self.workspace = workspace
        self.workspace_skills = workspace / "skills"
        self.builtin_skills = builtin_skills_dir or BUILTIN_SKILLS_DIR
    
    def list_skills(self, filter_unavailable: bool = True) -> list[dict[str, str]]:
        """
        List all available skills.
        
        Args:
            filter_unavailable: If True, filter out skills with unmet requirements.
        
        Returns:
            List of skill info dicts with 'name', 'path', 'source'.
        """
        skills = []
        
        # Workspace skills (highest priority)
        if self.workspace_skills.exists():
            for skill_dir in self.workspace_skills.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        skills.append({"name": skill_dir.name, "path": str(skill_file), "source": "workspace"})
        
        # Built-in skills
        if self.builtin_skills and self.builtin_skills.exists():
            for skill_dir in self.builtin_skills.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists() and not any(s["name"] == skill_dir.name for s in skills):
                        skills.append({"name": skill_dir.name, "path": str(skill_file), "source": "builtin"})
        
        # Filter by requirements
        if filter_unavailable:
            return [s for s in skills if self._check_requirements(self._get_skill_meta(s["name"]))]
        return skills
    
    def load_skill(self, name: str) -> str | None:
        """
        Load a skill by name.
        
        Args:
            name: Skill name (directory name).
        
        Returns:
            Skill content or None if not found.
        """
        skill_file = self._get_skill_file(name)
        return skill_file.read_text(encoding="utf-8") if skill_file else None
    
    def load_skills_for_context(self, skill_names: list[str]) -> str:
        """
        Load specific skills for inclusion in agent context.

        Args:
            skill_names: List of skill names to load.

        Returns:
            Formatted skills content.
        """
        parts = []
        for name in skill_names:
            skill_file = self._get_skill_file(name)
            content = skill_file.read_text(encoding="utf-8") if skill_file else None
            if content and skill_file:
                content = self._strip_frontmatter(content)
                content = self._resolve_secrets(name, content)
                content = resolve_skill_placeholders(content, skill_file.parent)
                parts.append(
                    f"### Skill: {name}\n\n"
                    f"Skill Root: {skill_file.parent}\n"
                    f"Skill File: {skill_file}\n\n"
                    f"{content}"
                )

        return "\n\n---\n\n".join(parts) if parts else ""
    
    def build_skills_summary(self) -> str:
        """
        Build a summary of all skills (name, description, path, availability).
        
        This is used for progressive loading - the agent can read the full
        skill content using read_file when needed.
        
        Returns:
            XML-formatted skills summary.
        """
        all_skills = self.list_skills(filter_unavailable=False)
        if not all_skills:
            return ""
        
        def escape_xml(s: str) -> str:
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        lines = ["<skills>"]
        for s in all_skills:
            name = escape_xml(s["name"])
            path = s["path"]
            desc = escape_xml(self._get_skill_description(s["name"]))
            skill_meta = self._get_skill_meta(s["name"])
            available = self._check_requirements(skill_meta)
            
            lines.append(f"  <skill available=\"{str(available).lower()}\">")
            lines.append(f"    <name>{name}</name>")
            lines.append(f"    <description>{desc}</description>")
            lines.append(f"    <location>{path}</location>")
            
            # Show missing requirements for unavailable skills
            if not available:
                missing = self._get_missing_requirements(skill_meta)
                if missing:
                    lines.append(f"    <requires>{escape_xml(missing)}</requires>")
            
            lines.append(f"  </skill>")
        lines.append("</skills>")
        
        return "\n".join(lines)
    
    def _get_missing_requirements(self, skill_meta: dict) -> str:
        """Get a description of missing requirements."""
        missing = []
        supported_os = skill_meta.get("os", [])
        current_os = platform.system().lower()
        if supported_os and current_os not in {os_name.lower() for os_name in supported_os}:
            missing.append(f"OS: {current_os} not in {', '.join(supported_os)}")

        requires = skill_meta.get("requires", {})
        for b in requires.get("bins", []):
            if not shutil.which(b):
                missing.append(f"CLI: {b}")
        for env in requires.get("env", []):
            if not os.environ.get(env):
                missing.append(f"ENV: {env}")
        for module in requires.get("python_modules", []):
            if importlib.util.find_spec(module) is None:
                missing.append(f"PYTHON: {module}")
        return ", ".join(missing)
    
    def _get_skill_description(self, name: str) -> str:
        """Get the description of a skill from its frontmatter."""
        meta = self.get_skill_metadata(name)
        if meta and meta.get("description"):
            return meta["description"]
        return name  # Fallback to skill name
    
    def _strip_frontmatter(self, content: str) -> str:
        """Remove YAML frontmatter from markdown content."""
        if content.startswith("---"):
            match = re.match(r"^---\n.*?\n---\n", content, re.DOTALL)
            if match:
                return content[match.end():].strip()
        return content
    
    def _parse_nanobot_metadata(self, raw: str) -> dict:
        """Parse nanobot metadata JSON from frontmatter."""
        try:
            data = json.loads(raw)
            return data.get("nanobot", {}) if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def _check_requirements(self, skill_meta: dict) -> bool:
        """Check if skill requirements are met (os, bins, env vars, Python modules)."""
        supported_os = skill_meta.get("os", [])
        current_os = platform.system().lower()
        if supported_os and current_os not in {os_name.lower() for os_name in supported_os}:
            return False

        requires = skill_meta.get("requires", {})
        for b in requires.get("bins", []):
            if not shutil.which(b):
                return False
        for env in requires.get("env", []):
            if not os.environ.get(env):
                return False
        for module in requires.get("python_modules", []):
            if importlib.util.find_spec(module) is None:
                return False
        return True
    
    def _get_skill_meta(self, name: str) -> dict:
        """Get nanobot metadata for a skill (cached in frontmatter)."""
        meta = self.get_skill_metadata(name) or {}
        return self._parse_nanobot_metadata(meta.get("metadata", ""))

    def _get_skill_file(self, name: str) -> Path | None:
        """Return the path to a skill's SKILL.md file."""
        workspace_skill = self.workspace_skills / name / "SKILL.md"
        if workspace_skill.exists():
            return workspace_skill

        if self.builtin_skills:
            builtin_skill = self.builtin_skills / name / "SKILL.md"
            if builtin_skill.exists():
                return builtin_skill

        return None
    
    def get_always_skills(self) -> list[str]:
        """Get skills marked as always=true that meet requirements."""
        result = []
        for s in self.list_skills(filter_unavailable=True):
            meta = self.get_skill_metadata(s["name"]) or {}
            skill_meta = self._parse_nanobot_metadata(meta.get("metadata", ""))
            if skill_meta.get("always") or meta.get("always"):
                result.append(s["name"])
        return result
    
    def match_skills(self, message: str) -> list[str]:
        """
        Match skills to a user message based on trigger keywords.

        Skills can define triggers in metadata:
            metadata: {"nanobot":{"triggers":["keyword1","keyword2"]}}

        Args:
            message: The user's message text.

        Returns:
            List of skill names whose triggers match the message.
        """
        matched = []
        msg_lower = message.lower()

        for s in self.list_skills(filter_unavailable=True):
            skill_meta = self._get_skill_meta(s["name"])
            triggers = skill_meta.get("triggers", [])
            if not triggers:
                continue
            for trigger in triggers:
                if trigger.lower() in msg_lower:
                    matched.append(s["name"])
                    break

        return matched

    def _resolve_secrets(self, name: str, content: str) -> str:
        """
        Resolve {{SECRET}} placeholders in skill content using metadata secrets mapping.

        Metadata format: {"nanobot":{"secrets":{"KEY":"~/path/to/file.txt"}}}
        Content placeholders: {{KEY}} will be replaced with file contents.
        Secret files must be located under ~/.nanobot/ for security.
        """
        skill_meta = self._get_skill_meta(name)
        secrets = skill_meta.get("secrets", {})
        if not secrets:
            return content

        allowed_dir = Path("~/.nanobot").expanduser().resolve()

        for key, file_path in secrets.items():
            placeholder = "{{" + key + "}}"
            if placeholder not in content:
                continue
            try:
                resolved = Path(file_path).expanduser().resolve()
                if not str(resolved).startswith(str(allowed_dir)):
                    logger.warning(f"Skill '{name}': secret '{key}' path outside ~/.nanobot/, skipping")
                    continue
                if not resolved.exists():
                    logger.warning(f"Skill '{name}': secret file not found: {resolved}")
                    continue
                value = resolved.read_text(encoding="utf-8").strip()
                if not value:
                    logger.warning(f"Skill '{name}': secret file is empty: {resolved}")
                    continue
                content = content.replace(placeholder, value)
            except Exception as e:
                logger.warning(f"Skill '{name}': failed to read secret '{key}': {e}")

        return content

    def get_skill_metadata(self, name: str) -> dict | None:
        """
        Get metadata from a skill's frontmatter.
        
        Args:
            name: Skill name.
        
        Returns:
            Metadata dict or None.
        """
        content = self.load_skill(name)
        if not content:
            return None
        
        if content.startswith("---"):
            match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if match:
                # Simple YAML parsing
                metadata = {}
                for line in match.group(1).split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip().strip('"\'')
                return metadata
        
        return None
