"""Check repository-wide file naming and Python dependency boundaries."""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from collections.abc import Callable, Iterable
from functools import lru_cache
from pathlib import Path, PurePosixPath, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "code-organization.json"


def normalized_path(value: str) -> str:
    return PurePosixPath(value.replace("\\", "/")).as_posix()


def case_conflicts(paths: Iterable[str]) -> list[str]:
    seen: dict[str, str] = {}
    conflicts: set[str] = set()
    for path in paths:
        parts = PurePosixPath(normalized_path(path)).parts
        for index in range(1, len(parts) + 1):
            prefix = "/".join(parts[:index])
            folded = prefix.casefold()
            previous = seen.get(folded)
            if previous is not None and previous != prefix:
                conflicts.add(f"{previous} <> {prefix}")
            else:
                seen[folded] = prefix
    return sorted(conflicts)


def unexpected_root_html(paths: Iterable[str], allowed: Iterable[str]) -> list[str]:
    allowed_names = set(allowed)
    return sorted(
        path
        for path in paths
        if "/" not in normalized_path(path)
        and PurePosixPath(normalized_path(path)).suffix.casefold() == ".html"
        and PurePosixPath(normalized_path(path)).name not in allowed_names
    )


def filter_existing_paths(paths: Iterable[str], exists: Callable[[str], bool]) -> list[str]:
    return [path for path in paths if exists(path)]


def module_path_candidates(module: str) -> tuple[str, ...]:
    parts = module.split(".")
    if not parts or any(not part.isidentifier() for part in parts):
        return ()
    stem = "/".join(parts)
    return (f"{stem}.py", f"{stem}/__init__.py")


def allowlist_violations(entries: object, backend_files: set[str]) -> list[str]:
    if not isinstance(entries, list):
        return ["backend allowlist must be a list"]
    violations: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            violations.append(f"backend allowlist entry {index} must be an object")
            continue
        source = entry.get("path")
        module = entry.get("module")
        if not isinstance(source, str) or not source:
            violations.append(f"backend allowlist entry {index} has no source path")
        else:
            source = normalized_path(source)
            if source.startswith("/") or ".." in PurePosixPath(source).parts or source not in backend_files:
                violations.append(f"backend allowlist source path does not exist: {source}")
        if not isinstance(module, str) or not module:
            violations.append(f"backend allowlist entry {index} has no target module")
        elif not any(candidate in backend_files for candidate in module_path_candidates(module)):
            violations.append(f"backend allowlist target module does not exist: {module}")
    return violations


def _is_forbidden(module: str, prefixes: Iterable[str]) -> bool:
    return any(module == prefix or module.startswith(prefix + ".") for prefix in prefixes)


def _relative_import_module(package: str, level: int, module: str | None) -> str | None:
    parts = package.split(".") if package else []
    ascend = level - 1
    if ascend > len(parts):
        return None
    base = parts[: len(parts) - ascend] if ascend else parts
    if module:
        base.extend(module.split("."))
    return ".".join(base)


def _package_for_source(path: str, runtime_root: str) -> str:
    source_parts = PurePosixPath(normalized_path(path)).parts
    root_parts = PurePosixPath(normalized_path(runtime_root)).parts
    relative_parts = source_parts[len(root_parts) :]
    parent_parts = relative_parts[:-1]
    return ".".join((PurePosixPath(runtime_root).name, *parent_parts))


def runtime_import_violations(
    sources: Iterable[tuple[str, str, str]], forbidden_prefixes: Iterable[str]
) -> list[str]:
    prefixes = tuple(forbidden_prefixes)
    violations: list[str] = []
    for path, source, package in sources:
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as error:
            violations.append(f"{path}:{error.lineno}: cannot parse Python source: {error.msg}")
            continue
        dynamic_names = {"__import__"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported_module = (
                    _relative_import_module(package, node.level, node.module)
                    if node.level
                    else node.module
                )
                modules = [imported_module] if imported_module else []
                if imported_module:
                    modules.extend(
                        f"{imported_module}.{alias.name}"
                        for alias in node.names
                        if alias.name != "*"
                    )
                elif node.level and node.module is None:
                    base = _relative_import_module(package, node.level, None)
                    if base is not None:
                        modules.extend(
                            f"{base}.{alias.name}"
                            for alias in node.names
                            if alias.name != "*"
                        )
                if node.module == "importlib":
                    dynamic_names.update(
                        alias.asname or alias.name for alias in node.names if alias.name == "import_module"
                    )
            else:
                modules = []
            for module in modules:
                if _is_forbidden(module, prefixes):
                    violations.append(f"{path}:{node.lineno}: runtime imports forbidden module {module}")

            if not isinstance(node, ast.Call):
                continue
            call_name = node.func.id if isinstance(node.func, ast.Name) else None
            if isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
                call_name = "import_module"
            if call_name not in dynamic_names or not node.args:
                continue
            argument = node.args[0]
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                if _is_forbidden(argument.value, prefixes):
                    violations.append(
                        f"{path}:{node.lineno}: runtime dynamically imports forbidden module {argument.value}"
                    )
    return sorted(set(violations))


def _git_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git ls-files failed: {detail}")
    paths = [
        normalized_path(item.decode("utf-8", errors="surrogateescape"))
        for item in result.stdout.split(b"\0")
        if item
    ]

    @lru_cache(maxsize=None)
    def directory_entries(relative_directory: str) -> frozenset[str]:
        directory = ROOT.joinpath(*PurePosixPath(relative_directory).parts) if relative_directory else ROOT
        try:
            return frozenset(entry.name for entry in os.scandir(directory))
        except OSError:
            return frozenset()

    def exists_with_exact_case(path: str) -> bool:
        parts = PurePosixPath(path).parts
        parent_parts: tuple[str, ...] = ()
        for part in parts:
            if part not in directory_entries("/".join(parent_parts)):
                return False
            parent_parts = (*parent_parts, part)
        return bool(parts)

    return filter_existing_paths(paths, exists_with_exact_case)


def _safe_relative_path(root: Path, value: str) -> Path | None:
    windows_path = PureWindowsPath(value)
    if windows_path.drive or windows_path.root:
        return None
    normalized = normalized_path(value)
    parts = PurePosixPath(normalized).parts
    if not parts or normalized.startswith("/") or ".." in parts:
        return None
    candidate = root.joinpath(*parts)
    if not candidate.resolve().is_relative_to(root.resolve()):
        return None
    return candidate


def check_repository(config: dict[str, object]) -> list[str]:
    violations: list[str] = []
    try:
        paths = _git_paths()
    except RuntimeError as error:
        return [str(error)]

    violations.extend(f"Git path case conflict: {item}" for item in case_conflicts(paths))
    root_html_allowlist = config.get("root_html_allowlist", [])
    if not isinstance(root_html_allowlist, list) or not all(isinstance(item, str) for item in root_html_allowlist):
        violations.append("root_html_allowlist must be a list of file names")
    else:
        root_html_paths = [
            path.name
            for path in ROOT.iterdir()
            if path.is_file() and path.suffix.casefold() == ".html"
        ]
        violations.extend(
            f"unexpected standalone root HTML file: {path}"
            for path in unexpected_root_html(root_html_paths, root_html_allowlist)
        )

    backend_root_value = config.get("backend_root")
    boundary_config_value = config.get("backend_boundaries_config")
    if not isinstance(backend_root_value, str) or not isinstance(boundary_config_value, str):
        return [*violations, "backend_root and backend_boundaries_config must be paths"]
    backend_root = _safe_relative_path(ROOT, backend_root_value)
    boundary_config_path = _safe_relative_path(ROOT, boundary_config_value)
    if backend_root is None or not backend_root.is_dir():
        return [*violations, f"backend root does not exist: {backend_root_value}"]
    if boundary_config_path is None or not boundary_config_path.is_file():
        return [*violations, f"backend boundaries config does not exist: {boundary_config_value}"]
    try:
        boundary_config = json.loads(boundary_config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [*violations, f"cannot read backend boundaries config: {error}"]
    backend_files = {
        path.relative_to(backend_root).as_posix()
        for path in (backend_root / "app").rglob("*.py")
        if path.is_file()
    }
    violations.extend(
        allowlist_violations(boundary_config.get("allowed_imports"), backend_files)
    )

    runtime_roots = config.get("runtime_python_roots", [])
    forbidden_prefixes = config.get("runtime_forbidden_import_prefixes", [])
    if not isinstance(runtime_roots, list) or not all(isinstance(item, str) for item in runtime_roots):
        violations.append("runtime_python_roots must be a list of paths")
    elif not isinstance(forbidden_prefixes, list) or not all(
        isinstance(item, str) for item in forbidden_prefixes
    ):
        violations.append("runtime_forbidden_import_prefixes must be a list of import prefixes")
    else:
        runtime_sources: list[tuple[str, str, str]] = []
        for value in runtime_roots:
            source_root = _safe_relative_path(ROOT, value)
            if source_root is None or not source_root.is_dir():
                violations.append(f"runtime Python root does not exist: {value}")
                continue
            for path in source_root.rglob("*.py"):
                if path.is_file():
                    relative_path = path.relative_to(ROOT).as_posix()
                    runtime_sources.append(
                        (relative_path, path.read_text(encoding="utf-8"), _package_for_source(relative_path, value))
                    )
        violations.extend(runtime_import_violations(runtime_sources, forbidden_prefixes))
    return sorted(set(violations))


def self_test() -> int:
    checks = {
        "rejects absolute and drive-relative configured roots": all(
            _safe_relative_path(ROOT, path) is None
            for path in ["C:/Windows", "C:Windows", "//server/share", "/outside", "../outside"]
        ),
        "accepts repository-relative configured roots": _safe_relative_path(ROOT, "backend/app") == ROOT / "backend/app",
        "detects case conflicts": bool(case_conflicts(["src/Feature/page.py", "src/feature/page.py"])),
        "accepts consistent casing": not case_conflicts(["src/feature/page.py", "src/feature/other.py"]),
        "allows configured root HTML": not unexpected_root_html(["index.html", "docs/page.html"], ["index.html"]),
        "detects extra root HTML": unexpected_root_html(["index.html", "demo.html"], ["index.html"]) == ["demo.html"],
        "requires exact root HTML casing": unexpected_root_html(["Index.html"], ["index.html"]) == ["Index.html"],
        "checks missing allowlist source and target": len(
            allowlist_violations(
                [
                    {"path": "app/old.py", "module": "app.modules.old.models"},
                    {"path": "app/modules/old/models.py", "module": "app.modules.missing.models"},
                ],
                {"app/modules/old/models.py"},
            )
        ) == 2,
        "detects runtime reverse imports": bool(
            runtime_import_violations(
                [("backend/app/example.py", "from backend.scripts import seed\n", "app")],
                ["backend.scripts", "backend.tests"],
            )
        ),
        "detects imported forbidden member": bool(
            runtime_import_violations(
                [("backend/app/example.py", "from backend import scripts\n", "app")],
                ["backend.scripts"],
            )
        ),
        "filters deleted Git paths": filter_existing_paths(
            ["deleted.py", "current.py"], lambda path: path == "current.py"
        ) == ["current.py"],
        "resolves relative reverse imports": bool(
            runtime_import_violations(
                [("backend/app/pkg/example.py", "from ..scripts import seed\n", "app.pkg")],
                ["app.scripts"],
            )
        ),
        "detects literal dynamic reverse imports": bool(
            runtime_import_violations(
                [
                    (
                        "backend/app/example.py",
                        "from importlib import import_module as load\nload('tests.data')\n",
                        "app",
                    )
                ],
                ["tests"],
            )
        ),
        "allows runtime imports of app modules": not runtime_import_violations(
            [("backend/app/example.py", "from app.modules.content.public import ContentPort\n", "app")],
            ["tests", "scripts"],
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    print(f"code-organization self-test: {'FAIL' if failed else 'PASS'} ({len(checks)} checks)")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    try:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"code-organization: cannot read config: {error}")
        return 1
    violations = check_repository(config)
    if violations:
        print("code-organization: FAIL")
        print("\n".join(violations))
        return 1
    print("code-organization: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
