"""
Skills Loader — reads SKILL.md files from the configured skills directory.

Two-phase loading strategy:
  1. Metadata-only (startup): load_skill_metadata() reads only the YAML
     frontmatter (name + description) for ALL skills — cheap, no large content
     is added to the system prompt yet.
  2. On-demand (at runtime): get_skill_content(name) reads and returns the
     full markdown body for a single named skill, called by the LLM via a tool.

Each skill is a markdown file with YAML frontmatter:

    ---
    name: skill-name
    description: Short trigger description
    ---

    # Skill Title
    ...full markdown content...

Usage:
    from src.agents.lead_agent.skills import load_skill_metadata, get_skill_content

    metas = load_skill_metadata()   # -> list[SkillMeta]  (startup)
    content = get_skill_content("deep-research")  # -> str  (on demand)
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class SkillMeta:
    """Lightweight skill descriptor — name and description only."""
    name: str
    description: str
    path: Path  # absolute path to SKILL.md (used by get_skill_content)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> dict[str, str]:
    """Extract key:value pairs from the YAML frontmatter block."""
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not fm_match:
        return {}
    fm: dict[str, str] = {}
    for line in fm_match.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def _strip_frontmatter(text: str) -> str:
    """Return the markdown body with frontmatter removed."""
    fm_match = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
    return text[fm_match.end():].strip() if fm_match else text.strip()


def _get_skills_dir() -> Path:
    """Resolve the skills directory from config.yaml or return the default."""
    try:
        import yaml

        config_path = Path(os.environ.get("FLOW_CONFIG_PATH", "config.yaml"))
        if config_path.exists():
            cfg = yaml.safe_load(config_path.read_text()) or {}
            skills_cfg = cfg.get("skills", {})
            if isinstance(skills_cfg, dict):
                raw_path = skills_cfg.get("path")
                if raw_path:
                    p = Path(raw_path)
                    if not p.is_absolute():
                        p = config_path.parent / p
                    return p
    except Exception:
        pass
    return Path("src/skills")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_skill_metadata() -> list[SkillMeta]:
    """Scan the skills directory and return metadata (name + description) only.

    No skill body content is read — this is intentionally cheap so that the
    system prompt stays small at startup.
    """
    skills_dir = _get_skills_dir()
    if not skills_dir.exists():
        return []

    metas: list[SkillMeta] = []
    for skill_md in sorted(skills_dir.rglob("SKILL.md")):
        try:
            text = skill_md.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[skills] Warning: could not read {skill_md}: {e}")
            continue

        fm = _parse_frontmatter(text)
        name = fm.get("name") or skill_md.parent.name
        description = fm.get("description", "")
        if name:
            metas.append(SkillMeta(name=name, description=description, path=skill_md))
            print(f"[skills] Registered skill '{name}' (metadata only)")

    return metas


def get_skill_content(name: str) -> str:
    """Load and return the full markdown body for the named skill.

    Searches the skills directory for a SKILL.md whose `name` frontmatter
    field matches (case-insensitive). Intended to be called at runtime via
    a LangChain tool — not at startup.

    Returns the full content string, or an error message if not found.
    """
    skills_dir = _get_skills_dir()
    if not skills_dir.exists():
        return f"[skills] Error: skills directory '{skills_dir}' not found."

    name_lower = name.strip().lower()
    for skill_md in sorted(skills_dir.rglob("SKILL.md")):
        try:
            text = skill_md.read_text(encoding="utf-8")
        except Exception:
            continue
        fm = _parse_frontmatter(text)
        skill_name = (fm.get("name") or skill_md.parent.name).strip().lower()
        if skill_name == name_lower:
            content = _strip_frontmatter(text)
            print(f"[skills] Loaded full content for skill '{name}' ({len(content)} chars)")
            return content

    available = ", ".join(
        m.name for m in load_skill_metadata()
    ) or "(none)"
    return f"[skills] Skill '{name}' not found. Available skills: {available}"

