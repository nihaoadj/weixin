"""Read-only structural checks for the repository's project-local skills."""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SKILLS_ROOT = ROOT / ".agents" / "skills"
SKILL_DIR = SKILLS_ROOT / "wx-engineering-standards"
REVIEW_SKILL_DIR = SKILLS_ROOT / "code-review-and-quality"
REQUIRED = (
    REVIEW_SKILL_DIR / "SKILL.md",
    REVIEW_SKILL_DIR / "LICENSE.txt",
    REVIEW_SKILL_DIR / "agents" / "openai.yaml",
    REVIEW_SKILL_DIR / "references" / "review-guide.md",
    SKILLS_ROOT / "screenshot" / "SKILL.md",
    SKILLS_ROOT / "screenshot" / "agents" / "openai.yaml",
    SKILLS_ROOT / "screenshot" / "scripts" / "ensure_macos_permissions.sh",
    SKILLS_ROOT / "screenshot" / "scripts" / "take_screenshot.ps1",
    SKILLS_ROOT / "screenshot" / "scripts" / "take_screenshot.py",
    SKILL_DIR / "SKILL.md",
    SKILL_DIR / "agents" / "openai.yaml",
    SKILL_DIR / "references" / "delivery-template.md",
    SKILLS_ROOT / "wx-frontend-ui" / "SKILL.md",
    SKILLS_ROOT / "wx-frontend-ui" / "agents" / "openai.yaml",
    SKILLS_ROOT / "wx-frontend-ui" / "references" / "quality-bar.md",
    SKILLS_ROOT / "wx-frontend-ui" / "references" / "verification.md",
)
REQUIRED_SKILLS = {
    "code-review-and-quality",
    "screenshot",
    "wx-engineering-standards",
    "wx-frontend-ui",
}
RETIRED_SKILLS = {
    "frontend-design",
    "frontend-ui-engineering",
    "web-design-guidelines",
}
ROUTING_PATHS = (
    ROOT / "package.json",
    ROOT / "src" / "App.vue",
    ROOT / "src" / "uni.scss",
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "product.md",
    ROOT / "docs" / "architecture.md",
    ROOT / "docs" / "development.md",
    ROOT / "docs" / "database.md",
    ROOT / "docs" / "security.md",
    ROOT / "docs" / "ui.md",
    ROOT / "docs" / "wechat.md",
    ROOT / "scripts" / "frontend-boundaries.mjs",
    ROOT / "backend" / "scripts" / "check_boundaries.py",
    ROOT / "config" / "frontend-boundaries.json",
    ROOT / "config" / "backend-boundaries.json",
)
MODULES = (
    "identity",
    "qa",
    "reports",
    "content",
    "training",
    "learning",
    "classroom",
    "analytics",
)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---(?:\s*\n|\Z)", re.DOTALL)
FIELD_RE = re.compile(r"^([a-zA-Z][\w-]*):\s*[\"']?(.*?)[\"']?\s*$")
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
INTERFACE_FIELD_RE = re.compile(r"^  ([a-z][a-z0-9_]*):\s*(['\"])(.*?)\2\s*$")
REQUIRED_INTERFACE_FIELDS = {
    "display_name",
    "short_description",
    "default_prompt",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def skill_directories() -> list[Path]:
    if not SKILLS_ROOT.is_dir():
        return []
    return sorted(path for path in SKILLS_ROOT.iterdir() if path.is_dir())


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        field = FIELD_RE.match(line)
        if field:
            fields[field.group(1)] = field.group(2)
    return fields


def parse_interface_metadata(path: Path) -> tuple[dict[str, str], list[str]]:
    fields: dict[str, str] = {}
    errors: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        interface_index = lines.index("interface:")
    except ValueError:
        return fields, [f"missing interface mapping: {display_path(path)}"]

    for line in lines[interface_index + 1 :]:
        if line and not line.startswith("  "):
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = INTERFACE_FIELD_RE.fullmatch(line)
        if not match:
            errors.append(
                f"interface string fields must be quoted: {display_path(path)}: {line.strip()}"
            )
            continue
        key, _, value = match.groups()
        if key in fields:
            errors.append(f"duplicate interface field {key!r}: {display_path(path)}")
        fields[key] = value
    return fields, errors


def check_required_files() -> list[str]:
    errors: list[str] = []
    for path in REQUIRED:
        if not path.is_file():
            errors.append(f"missing required file: {display_path(path)}")
    agents = ROOT / "AGENTS.md"
    if not agents.is_file():
        errors.append("missing root AGENTS.md")
    return errors


def check_skill_catalog() -> list[str]:
    errors: list[str] = []
    directories = skill_directories()
    folder_names = {path.name for path in directories}
    for name in sorted(REQUIRED_SKILLS - folder_names):
        errors.append(f"missing required project skill: {name}")
    for name in sorted(folder_names - REQUIRED_SKILLS):
        errors.append(f"unexpected project skill outside the T23 catalog: {name}")
    for name in sorted(RETIRED_SKILLS & folder_names):
        errors.append(f"retired overlapping skill must not return: {name}")

    declared_names: dict[str, Path] = {}
    for directory in directories:
        skill_file = directory / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"skill directory has no SKILL.md: {display_path(directory)}")
            continue
        frontmatter = parse_frontmatter(skill_file)
        declared_name = frontmatter.get("name", "")
        description = frontmatter.get("description", "")
        if not declared_name:
            errors.append(f"missing frontmatter name: {display_path(skill_file)}")
        else:
            if not SKILL_NAME_RE.fullmatch(declared_name) or len(declared_name) > 64:
                errors.append(
                    f"invalid skill name {declared_name!r}: {display_path(skill_file)}"
                )
            if declared_name != directory.name:
                errors.append(
                    f"skill name/folder mismatch: {directory.name} declares {declared_name}"
                )
            if declared_name in declared_names:
                first = display_path(declared_names[declared_name])
                errors.append(
                    f"duplicate skill name {declared_name!r}: "
                    f"{first} and {display_path(skill_file)}"
                )
            else:
                declared_names[declared_name] = skill_file
        if not description.strip():
            errors.append(
                f"missing frontmatter description: {display_path(skill_file)}"
            )

        metadata = directory / "agents" / "openai.yaml"
        if not metadata.is_file():
            errors.append(f"missing skill metadata: {display_path(metadata)}")
        elif declared_name:
            interface, metadata_errors = parse_interface_metadata(metadata)
            errors.extend(metadata_errors)
            for field in sorted(REQUIRED_INTERFACE_FIELDS - interface.keys()):
                errors.append(
                    f"missing openai.yaml interface.{field}: {display_path(metadata)}"
                )
            for field in sorted(REQUIRED_INTERFACE_FIELDS & interface.keys()):
                if not interface[field].strip():
                    errors.append(
                        f"empty openai.yaml interface.{field}: {display_path(metadata)}"
                    )
            default_prompt = interface.get("default_prompt", "")
            if default_prompt and f"${declared_name}" not in default_prompt:
                errors.append(
                    "openai.yaml default prompt must mention "
                    f"${declared_name}: {display_path(metadata)}"
                )
            short_description = interface.get("short_description", "")
            if short_description and not 25 <= len(short_description) <= 64:
                errors.append(
                    "openai.yaml short_description must contain 25-64 characters: "
                    f"{display_path(metadata)}"
                )
            for icon_field in ("icon_small", "icon_large"):
                icon = interface.get(icon_field)
                if icon and not (metadata.parent.parent / icon).is_file():
                    errors.append(
                        f"missing {icon_field} asset in {display_path(metadata)}: {icon}"
                    )
    return errors


def check_routing_references() -> list[str]:
    errors: list[str] = []
    for path in ROUTING_PATHS:
        if not path.is_file():
            errors.append(f"missing routing reference: {display_path(path)}")
    for module in MODULES:
        module_root = ROOT / "backend" / "app" / "modules" / module
        for name in ("api", "application", "domain", "infrastructure"):
            if not (module_root / name).is_dir():
                errors.append(
                    f"missing backend module layer: app/modules/{module}/{name}"
                )
        for name in ("public.py", "wiring.py"):
            if not (module_root / name).is_file():
                errors.append(
                    f"missing backend module interface: app/modules/{module}/{name}"
                )
    if (SKILL_DIR / "SKILL.md").is_file():
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        for marker in (
            "R05",
            "scripts/frontend-boundaries.mjs",
            "backend/scripts/check_boundaries.py",
        ):
            if marker not in skill_text:
                errors.append(f"missing routing marker {marker!r} in SKILL.md")
    review_skill = SKILLS_ROOT / "code-review-and-quality" / "SKILL.md"
    if review_skill.is_file():
        review_text = review_skill.read_text(encoding="utf-8")
        for marker in (
            "AGENTS.md",
            "wx-engineering-standards",
            "findings",
            "Do not modify",
        ):
            if marker not in review_text:
                errors.append(
                    f"missing review routing marker {marker!r} in "
                    "code-review-and-quality/SKILL.md"
                )
        for forbidden in (
            "Every change gets reviewed before merge",
            "security-and-hardening",
            "performance-optimization",
        ):
            if forbidden in review_text:
                errors.append(
                    f"forbidden upstream coupling {forbidden!r} in "
                    "code-review-and-quality/SKILL.md"
                )
    return errors


def check_markdown_links() -> list[str]:
    errors: list[str] = []
    for directory in skill_directories():
        for markdown in directory.rglob("*.md"):
            for match in LINK_RE.finditer(markdown.read_text(encoding="utf-8")):
                target = match.group(1).split("#", 1)[0]
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                resolved = (markdown.parent / target).resolve()
                if not resolved.is_file():
                    errors.append(f"broken link in {display_path(markdown)}: {target}")
    return errors


def check_state_labels() -> list[str]:
    skill_path = SKILL_DIR / "SKILL.md"
    template_path = SKILL_DIR / "references" / "delivery-template.md"
    if not skill_path.is_file() or not template_path.is_file():
        return []
    skill_text = skill_path.read_text(encoding="utf-8")
    template_text = template_path.read_text(encoding="utf-8")
    errors: list[str] = []
    for marker, text, label in (
        ("当前事实", skill_text, "SKILL.md"),
        ("计划目标", skill_text, "SKILL.md"),
        ("当前事实", template_text, "delivery-template.md"),
        ("计划目标", template_text, "delivery-template.md"),
    ):
        if marker not in text:
            errors.append(f"missing state label {marker!r} in {label}")
    return errors


def write_test_skill(root: Path, name: str, declared_name: str | None = None) -> None:
    skill_root = root / name
    (skill_root / "agents").mkdir(parents=True, exist_ok=True)
    actual_name = declared_name or name
    (skill_root / "SKILL.md").write_text(
        f"---\nname: {actual_name}\ndescription: Test skill.\n---\n",
        encoding="utf-8",
    )
    (skill_root / "agents" / "openai.yaml").write_text(
        "interface:\n"
        f'  display_name: "{name}"\n'
        '  short_description: "Reliable project skill metadata"\n'
        f'  default_prompt: "Use ${actual_name} for this test."\n',
        encoding="utf-8",
    )


def remove_test_skill(path: Path) -> None:
    for child in sorted(path.rglob("*"), reverse=True):
        child.unlink() if child.is_file() else child.rmdir()
    path.rmdir()


def run_self_tests() -> int:
    global SKILLS_ROOT

    original_root = SKILLS_ROOT
    failures: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="wx-skill-self-test-") as temp_dir:
            SKILLS_ROOT = Path(temp_dir)
            for name in sorted(REQUIRED_SKILLS):
                write_test_skill(SKILLS_ROOT, name)
            if errors := check_skill_catalog():
                failures.append(f"valid catalog rejected: {errors}")

            remove_test_skill(SKILLS_ROOT / "code-review-and-quality")
            errors = check_skill_catalog()
            if not any("missing required project skill" in error for error in errors):
                failures.append("missing review skill was not rejected")
            write_test_skill(SKILLS_ROOT, "code-review-and-quality")

            review_skill = SKILLS_ROOT / "code-review-and-quality" / "SKILL.md"
            review_skill.write_text(
                review_skill.read_text(encoding="utf-8")
                + "Every change gets reviewed before merge.\n",
                encoding="utf-8",
            )
            errors = check_routing_references()
            if not any("forbidden upstream coupling" in error for error in errors):
                failures.append("forbidden upstream review coupling was not rejected")
            write_test_skill(SKILLS_ROOT, "code-review-and-quality")

            write_test_skill(SKILLS_ROOT, "frontend-design")
            errors = check_skill_catalog()
            if not any("retired overlapping skill" in error for error in errors):
                failures.append("retired skill was not rejected")
            remove_test_skill(SKILLS_ROOT / "frontend-design")

            write_test_skill(SKILLS_ROOT, "unplanned-skill")
            errors = check_skill_catalog()
            if not any("unexpected project skill" in error for error in errors):
                failures.append("unexpected sixth skill was not rejected")
            remove_test_skill(SKILLS_ROOT / "unplanned-skill")

            write_test_skill(
                SKILLS_ROOT, "duplicate-wx-frontend-ui", declared_name="wx-frontend-ui"
            )
            errors = check_skill_catalog()
            if not any("duplicate skill name" in error for error in errors):
                failures.append("duplicate skill name was not rejected")
            remove_test_skill(SKILLS_ROOT / "duplicate-wx-frontend-ui")

            write_test_skill(SKILLS_ROOT, "invalid_name")
            errors = check_skill_catalog()
            if not any("invalid skill name" in error for error in errors):
                failures.append("invalid skill name was not rejected")
            remove_test_skill(SKILLS_ROOT / "invalid_name")

            mismatch = SKILLS_ROOT / "wx-frontend-ui" / "SKILL.md"
            mismatch.write_text(
                "---\nname: wrong-name\ndescription: Test skill.\n---\n",
                encoding="utf-8",
            )
            errors = check_skill_catalog()
            if not any("name/folder mismatch" in error for error in errors):
                failures.append("name/folder mismatch was not rejected")
            write_test_skill(SKILLS_ROOT, "wx-frontend-ui")

            metadata = SKILLS_ROOT / "screenshot" / "agents" / "openai.yaml"
            metadata.unlink()
            errors = check_skill_catalog()
            if not any("missing skill metadata" in error for error in errors):
                failures.append("missing skill metadata was not rejected")
            write_test_skill(SKILLS_ROOT, "screenshot")

            metadata.write_text(
                "interface:\n"
                '  display_name: "screenshot"\n'
                '  short_description: "Reliable project skill metadata"\n'
                '  default_prompt: "Missing the explicit skill invocation."\n',
                encoding="utf-8",
            )
            errors = check_skill_catalog()
            if not any("default prompt must mention" in error for error in errors):
                failures.append("invalid skill default prompt was not rejected")
            write_test_skill(SKILLS_ROOT, "screenshot")

            metadata.write_text(
                "interface:\n"
                '  display_name: "screenshot"\n'
                "  short_description: unquoted metadata is unstable\n"
                '  default_prompt: "Use $screenshot for this test."\n',
                encoding="utf-8",
            )
            errors = check_skill_catalog()
            if not any("must be quoted" in error for error in errors):
                failures.append("unquoted interface metadata was not rejected")
            write_test_skill(SKILLS_ROOT, "screenshot")

            metadata.write_text(
                "interface:\n"
                '  display_name: ""\n'
                '  short_description: "short"\n'
                '  default_prompt: "Use $screenshot for this test."\n'
                '  icon_small: "./assets/missing.png"\n',
                encoding="utf-8",
            )
            errors = check_skill_catalog()
            for expected, label in (
                ("empty openai.yaml interface.display_name", "empty display name"),
                ("short_description must contain 25-64", "short description length"),
                ("missing icon_small asset", "missing icon asset"),
            ):
                if not any(expected in error for error in errors):
                    failures.append(f"{label} was not rejected")
            write_test_skill(SKILLS_ROOT, "screenshot")

            broken = SKILLS_ROOT / "wx-frontend-ui" / "SKILL.md"
            broken.write_text(
                broken.read_text(encoding="utf-8") + "[missing](missing.md)\n",
                encoding="utf-8",
            )
            errors = check_markdown_links()
            if not any("broken link" in error for error in errors):
                failures.append("broken local link was not rejected")
    finally:
        SKILLS_ROOT = original_root

    if failures:
        for failure in failures:
            fail(f"self-test: {failure}")
        return 1
    print("PASS: project skill validator negative self-tests passed.")
    return 0


def main() -> int:
    if len(sys.argv) > 1:
        if sys.argv[1:] == ["--self-test"]:
            return run_self_tests()
        fail(f"unsupported arguments: {' '.join(sys.argv[1:])}")
        return 2
    errors = check_required_files()
    errors.extend(check_skill_catalog())
    errors.extend(check_routing_references())
    errors.extend(check_markdown_links())
    errors.extend(check_state_labels())
    if errors:
        for error in errors:
            fail(error)
        return 1
    print(
        "PASS: project skill catalog, structure, links, metadata, and routing are valid."
    )
    print(
        "INFO: read-only self-check; no backend tests, migrations, E2E, network, "
        "or contract generation run."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
