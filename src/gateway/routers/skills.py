"""
Skills Router — endpoints for listing and reading agent skills.

GET  /api/skills              — list all skills (name + description from frontmatter)
GET  /api/skills/{name}/content — return full SKILL.md content

Skills are discovered by scanning src/skills/*/SKILL.md relative to the
project root.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/skills", tags=["skills"])

# Project root is three levels above this file: src/gateway/routers/skills.py
_PROJECT_ROOT = Path(__file__).parents[3]
_SKILLS_DIR = _PROJECT_ROOT / "src" / "skills"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Extract YAML frontmatter fields from a SKILL.md file and return (metadata, body).

    Frontmatter is the block delimited by ``---`` at the top of the file.
    Only simple key: value pairs are supported (no nested YAML).
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not match:
        return {}, text
    
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields, match.group(2)


def _format_frontmatter_as_table(meta: dict[str, str]) -> str:
    """Convert a dictionary of frontmatter into a Markdown table."""
    if not meta:
        return ""
    
    table = "| Field | Value |\n|---|---|\n"
    for k, v in meta.items():
        safe_v = v.replace("|", "\\|")
        table += f"| **{k}** | {safe_v} |\n"
    
    return table + "\n"


def _discover_skills() -> list[dict[str, str]]:
    """Return a list of dicts with ``name`` and ``description`` for each skill."""
    results: list[dict[str, str]] = []
    if not _SKILLS_DIR.is_dir():
        return results
    for skill_dir in sorted(_SKILLS_DIR.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if skill_dir.is_dir() and skill_md.is_file():
            text = skill_md.read_text(encoding="utf-8")
            meta, _ = _parse_frontmatter(text)
            results.append(
                {
                    "name": meta.get("name", skill_dir.name),
                    "description": meta.get("description", ""),
                }
            )
    return results


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #

class SkillSummary(BaseModel):
    name: str
    description: str


class SkillContent(BaseModel):
    name: str
    content: str


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@router.get("", response_model=list[SkillSummary])
async def list_skills() -> list[SkillSummary]:
    """List all available skills with their names and descriptions."""
    return [SkillSummary(**s) for s in _discover_skills()]


@router.get("/{name}/content", response_model=SkillContent)
async def get_skill_content(name: str) -> SkillContent:
    """Return the full SKILL.md content for the given skill name."""
    if not _SKILLS_DIR.is_dir():
        raise HTTPException(status_code=404, detail="Skills directory not found")

    for skill_dir in _SKILLS_DIR.iterdir():
        skill_md = skill_dir / "SKILL.md"
        if skill_dir.is_dir() and skill_md.is_file():
            text = skill_md.read_text(encoding="utf-8")
            meta, body = _parse_frontmatter(text)
            skill_name = meta.get("name", skill_dir.name)
            if skill_name == name:
                table_md = _format_frontmatter_as_table(meta)
                return SkillContent(name=skill_name, content=table_md + body)

    raise HTTPException(status_code=404, detail=f"Skill not found: {name}")
