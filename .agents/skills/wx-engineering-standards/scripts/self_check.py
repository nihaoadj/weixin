"""Read-only structural checks for the project-local engineering skill."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = ROOT / ".agents" / "skills" / "wx-engineering-standards"
REQUIRED = (
    SKILL_DIR / "SKILL.md",
    SKILL_DIR / "agents" / "openai.yaml",
    SKILL_DIR / "references" / "delivery-template.md",
)
ROUTING_PATHS = (
    ROOT / "docs" / "architecture.md",
    ROOT / "docs" / "data-layer.md",
    ROOT / "docs" / "development.md",
    ROOT / "docs" / "database.md",
    ROOT / "docs" / "security.md",
    ROOT / "docs" / "deployment.md",
    ROOT / "docs" / "adr" / "0001-data-layer-contracts.md",
    ROOT / "docs" / "frontend-public-interfaces.md",
    ROOT / "docs" / "backend-module-map.md",
    ROOT / "scripts" / "frontend-boundaries.mjs",
    ROOT / "backend" / "scripts" / "check_boundaries.py",
    ROOT / "config" / "frontend-boundaries.json",
    ROOT / "config" / "backend-boundaries.json",
)
MODULES = ("identity", "qa", "reports", "content", "training", "learning", "classroom", "analytics")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def fail(message: str) -> None:
    print(f"FAIL: {message}")


def check_required_files() -> list[str]:
    errors: list[str] = []
    for path in REQUIRED:
        if not path.is_file():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")
    agents = ROOT / "AGENTS.md"
    if not agents.is_file():
        errors.append("missing root AGENTS.md")
    return errors


def check_routing_references() -> list[str]:
    errors: list[str] = []
    for path in ROUTING_PATHS:
        if not path.is_file():
            errors.append(f"missing routing reference: {path.relative_to(ROOT)}")
    for module in MODULES:
        module_root = ROOT / "backend" / "app" / "modules" / module
        for name in ("api", "application", "domain", "infrastructure"):
            if not (module_root / name).is_dir():
                errors.append(f"missing backend module layer: app/modules/{module}/{name}")
        for name in ("public.py", "wiring.py"):
            if not (module_root / name).is_file():
                errors.append(f"missing backend module interface: app/modules/{module}/{name}")
    skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    for marker in ("R05", "scripts/frontend-boundaries.mjs", "backend/scripts/check_boundaries.py"):
        if marker not in skill_text:
            errors.append(f"missing routing marker {marker!r} in SKILL.md")
    return errors


def check_markdown_links() -> list[str]:
    errors: list[str] = []
    for markdown in (SKILL_DIR / "SKILL.md", SKILL_DIR / "references" / "delivery-template.md"):
        if not markdown.is_file():
            continue
        for match in LINK_RE.finditer(markdown.read_text(encoding="utf-8")):
            target = match.group(1).split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (markdown.parent / target).resolve()
            if not resolved.is_file():
                errors.append(
                    f"broken link in {markdown.relative_to(ROOT)}: {target}"
                )
    return errors


def check_state_labels() -> list[str]:
    skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    template_text = (SKILL_DIR / "references" / "delivery-template.md").read_text(
        encoding="utf-8"
    )
    errors: list[str] = []
    for marker, text, label in (
        ("当前事实", skill_text, "SKILL.md"),
        ("计划目标", skill_text, "SKILL.md"),
        ("当前事实", template_text, "delivery-template.md"),
        ("计划目标", template_text, "delivery-template.md"),
    ):
        if marker not in text:
            errors.append(f"missing state label {marker!r} in {label}")
    if "T01/T02" not in skill_text:
        errors.append("SKILL.md must state that T01/T02 acceptance is not implied")
    return errors


def main() -> int:
    errors = check_required_files()
    errors.extend(check_routing_references())
    errors.extend(check_markdown_links())
    if all(path.is_file() for path in REQUIRED):
        errors.extend(check_state_labels())
    if errors:
        for error in errors:
            fail(error)
        return 1
    print("PASS: wx-engineering-standards structure, links, and state labels are valid.")
    print("INFO: read-only self-check; no backend tests, migrations, E2E, network, or contract generation run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
