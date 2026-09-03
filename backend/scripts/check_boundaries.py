"""Static dependency, layering, and transaction-boundary checks for T04.

The checker deliberately works from the Python AST rather than from directory
names. It resolves relative imports, re-exported symbols, type-only imports,
and project import cycles before applying the configured layer rules. The
``--self-test`` suite contains the negative probes that previously slipped
through the directory-only checker.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "app"
CONFIG_PATH = ROOT.parent / "config" / "backend-boundaries.json"

FRAMEWORK_ROOTS = ("fastapi", "starlette", "sqlalchemy", "httpx", "pydantic")
CORE_FORBIDDEN_ROOTS = FRAMEWORK_ROOTS + ("app.db", "app.dependencies", "app.models", "app.schemas")
APPLICATION_FORBIDDEN_ROOTS = CORE_FORBIDDEN_ROOTS + ("app.services",)
DB_WRITE_METHODS = {
    "add",
    "add_all",
    "begin",
    "commit",
    "delete",
    "execute",
    "flush",
    "merge",
    "refresh",
    "rollback",
}
DB_READ_METHODS = {"execute", "get", "scalar", "scalars", "query", "refresh"}
DB_IMPORT_ROOTS = ("sqlalchemy", "app.db")
LAYER_NAMES = {"api", "application", "domain", "infrastructure", "public", "wiring"}
SHARED_ALLOWED_ROLES = {"shared"}
PLATFORM_ALLOWED_ROLES = {"platform", "shared"}


@dataclass(frozen=True)
class ImportRef:
    source: str
    current_module: str
    raw_module: str
    level: int
    names: tuple[str, ...]
    aliases: tuple[str, ...]
    node: ast.AST
    type_only: bool


@dataclass(frozen=True)
class SourceInfo:
    path: str
    module: str
    role: str
    business_module: str | None
    layer: str | None
    tree: ast.Module
    source: str


def _normalize_path(value: str) -> str:
    return value.replace("\\", "/").lstrip("./")


def _module_for_path(relative_path: str) -> str:
    normalized = _normalize_path(relative_path)
    parts = normalized.split("/")
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _classify_path(relative_path: str) -> tuple[str, str | None, str | None]:
    normalized = _normalize_path(relative_path)
    parts = normalized.split("/")
    module_names = {
        "identity",
        "qa",
        "reports",
        "content",
        "training",
        "learning",
        "classroom",
        "analytics",
    }
    if len(parts) >= 4 and parts[0:2] == ["app", "modules"] and (
        parts[2] in module_names or parts[2].isidentifier()
    ):
        business_module = parts[2]
        layer = parts[3] if parts[3] in LAYER_NAMES else None
        if layer is None and parts[3] == "wiring.py":
            layer = "wiring"
        if layer is None and parts[3] == "public.py":
            layer = "public"
        return (layer or "module", business_module, layer)
    if len(parts) >= 2 and parts[0:2] == ["app", "bootstrap"]:
        return ("bootstrap", None, None)
    if len(parts) >= 2 and parts[0:2] == ["app", "core"]:
        return ("platform", None, None)
    if len(parts) >= 2 and parts[0:2] == ["app", "platform"]:
        return ("platform", None, None)
    if len(parts) >= 2 and parts[0:2] == ["app", "shared"]:
        return ("shared", None, None)
    if len(parts) >= 2 and parts[0:2] == ["app", "api"]:
        return ("api_compat", None, None)
    if len(parts) >= 2 and parts[0:2] == ["app", "models"]:
        return ("models", None, None)
    if len(parts) >= 2 and parts[0:2] == ["app", "schemas"]:
        return ("schemas", None, None)
    if len(parts) >= 2 and parts[0:2] == ["app", "services"]:
        return ("legacy", None, None)
    if normalized in {"app/db.py", "app/main.py"}:
        return ("bootstrap", None, None)
    if normalized in {"app/dependencies.py", "app/errors.py"}:
        return ("api_compat", None, None)
    if normalized.startswith("app/"):
        return ("app_root", None, None)
    return ("external", None, None)


def _source_info(source: str, relative_path: str) -> SourceInfo | None:
    normalized = _normalize_path(relative_path)
    try:
        tree = ast.parse(source, filename=normalized)
    except SyntaxError:
        return None
    role, business_module, layer = _classify_path(normalized)
    return SourceInfo(
        path=normalized,
        module=_module_for_path(normalized),
        role=role,
        business_module=business_module,
        layer=layer,
        tree=tree,
        source=source,
    )


def _package_for_source(info: SourceInfo) -> tuple[str, ...]:
    parts = info.module.split(".")
    if info.path.endswith("/__init__.py") or info.path.endswith("\\__init__.py"):
        return tuple(parts)
    return tuple(parts[:-1])


def _resolve_relative(info: SourceInfo, level: int, module: str) -> str:
    if level == 0:
        return module
    package = _package_for_source(info)
    if level > len(package) + 1:
        return module
    base = package[: len(package) - (level - 1)]
    return ".".join((*base, module)) if module else ".".join(base)


def _inside_type_checking(tree: ast.AST, node: ast.AST) -> bool:
    """Return whether an import is nested under a TYPE_CHECKING guard."""

    parents: dict[int, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent
    current = parents.get(id(node))
    while current is not None:
        if isinstance(current, ast.If):
            test = current.test
            if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
                return True
            if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
                return True
        current = parents.get(id(current))
    return False


def _imports_from_tree(info: SourceInfo) -> list[ImportRef]:
    result: list[ImportRef] = []
    for node in ast.walk(info.tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                result.append(
                    ImportRef(
                        source=info.path,
                        current_module=info.module,
                        raw_module=alias.name,
                        level=0,
                        names=(bound,),
                        aliases=(bound,),
                        node=node,
                        type_only=_inside_type_checking(info.tree, node),
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            result.append(
                ImportRef(
                    source=info.path,
                    current_module=info.module,
                    raw_module=node.module or "",
                    level=node.level,
                    names=tuple(alias.name for alias in node.names),
                    aliases=tuple(alias.asname or alias.name for alias in node.names),
                    node=node,
                    type_only=_inside_type_checking(info.tree, node),
                )
            )
    return result


def _imports(tree: ast.AST) -> list[tuple[str, ast.AST]]:
    """Backward-compatible simple import view used by older local probes."""

    result: list[tuple[str, ast.AST]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend((alias.name, node) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            result.append((node.module or "", node))
    return result


class DependencyIndex:
    """Parsed project sources and re-export bindings."""

    def __init__(self, sources: Iterable[SourceInfo]) -> None:
        self.sources = {source.module: source for source in sources}
        self.bindings: dict[str, dict[str, tuple[str, str | None]]] = {}
        for source in self.sources.values():
            bindings: dict[str, tuple[str, str | None]] = {}
            for node in source.tree.body:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        bindings[alias.asname or alias.name.split(".")[0]] = (alias.name, None)
                elif isinstance(node, ast.ImportFrom):
                    base = _resolve_relative(source, node.level, node.module or "")
                    for alias in node.names:
                        if alias.name != "*":
                            bindings[alias.asname or alias.name] = (base, alias.name)
                elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                    bindings[node.name] = (source.module, None)
                elif isinstance(node, ast.Assign | ast.AnnAssign):
                    targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
                    for target in targets:
                        if isinstance(target, ast.Name):
                            bindings[target.id] = (source.module, None)
            self.bindings[source.module] = bindings

    def is_project_module(self, module: str) -> bool:
        return module in self.sources

    def resolve_symbol(self, module: str, name: str, seen: set[tuple[str, str]] | None = None) -> str | None:
        if not module or module not in self.sources:
            return None
        visited = set() if seen is None else seen
        key = (module, name)
        if key in visited:
            return module
        visited.add(key)
        candidate = f"{module}.{name}"
        if candidate in self.sources:
            return candidate
        binding = self.bindings.get(module, {}).get(name)
        if binding is None:
            return module
        target_module, target_symbol = binding
        if target_symbol is None:
            return target_module if self.is_project_module(target_module) else module
        resolved = self.resolve_symbol(target_module, target_symbol, visited)
        return resolved or target_module

    def targets(self, ref: ImportRef) -> tuple[str, ...]:
        source = self.sources.get(ref.current_module)
        if source is None and ref.level:
            return ()
        base = ref.raw_module if source is None else _resolve_relative(source, ref.level, ref.raw_module)
        if not ref.names:
            return (base,)
        targets: list[str] = []
        for name in ref.names:
            if name == "*":
                targets.append(base)
                continue
            candidate = f"{base}.{name}" if base else name
            if self.is_project_module(candidate):
                targets.append(candidate)
                continue
            if base == "app":
                targets.append(candidate)
                continue
            resolved = self.resolve_symbol(base, name)
            targets.append(resolved or base)
        return tuple(dict.fromkeys(targets))


def _build_index() -> DependencyIndex:
    sources: list[SourceInfo] = []
    for path in APP_ROOT.rglob("*.py"):
        relative = path.relative_to(ROOT).as_posix()
        info = _source_info(path.read_text(encoding="utf-8"), relative)
        if info is not None:
            sources.append(info)
    return DependencyIndex(sources)


def _matches(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(f"{prefix}.")


def _is_allowed_import(path: str, target: str, config: dict[str, object]) -> bool:
    allowed = config.get("allowed_imports", [])
    if not isinstance(allowed, list):
        return False
    return any(
        isinstance(item, dict)
        and item.get("path") == path
        and item.get("module") == target
        for item in allowed
    )


def _role_for_target(target: str, index: DependencyIndex) -> tuple[str, str | None, str | None]:
    source = index.sources.get(target)
    if source is not None:
        return source.role, source.business_module, source.layer
    if target.startswith("app.modules."):
        parts = target.split(".")
        if len(parts) >= 4:
            return parts[3], parts[2], parts[3] if parts[3] in LAYER_NAMES else None
    if target.startswith("app.bootstrap"):
        return "bootstrap", None, None
    if target.startswith("app.platform") or target.startswith("app.core"):
        return "platform", None, None
    if target.startswith("app.shared"):
        return "shared", None, None
    if target.startswith("app.api"):
        return "api_compat", None, None
    if target.startswith("app.models"):
        return "models", None, None
    if target.startswith("app.schemas"):
        return "schemas", None, None
    if target.startswith("app.services"):
        return "legacy", None, None
    return "external", None, None


def _is_orm_model_type_reference(
    info: SourceInfo, ref: ImportRef, targets: tuple[str, ...], index: DependencyIndex
) -> bool:
    """Allow only type-only cross-module references needed by ORM relationships."""

    if info.layer != "infrastructure" or not info.path.endswith("/models.py") or not ref.type_only:
        return False
    return bool(targets) and all(_role_for_target(target, index)[0] == "infrastructure" for target in targets)


def _target_module(info: SourceInfo, ref: ImportRef, index: DependencyIndex) -> tuple[str, ...]:
    targets = index.targets(ref)
    if targets:
        return targets
    base = _resolve_relative(info, ref.level, ref.raw_module)
    if ref.raw_module == "app" and ref.names:
        return tuple(f"{base}.{name}" for name in ref.names)
    return (base,)


def _bound_dict_object_names(info: SourceInfo) -> set[str]:
    names: set[str] = set()

    def is_dict_object(annotation: ast.expr | None) -> bool:
        if not isinstance(annotation, ast.Subscript):
            return False
        value = annotation.value
        if not (isinstance(value, ast.Name) and value.id == "dict"):
            return False
        elements = annotation.slice.elts if isinstance(annotation.slice, ast.Tuple) else ()
        return len(elements) == 2 and isinstance(elements[1], ast.Name) and elements[1].id == "object"

    for node in ast.walk(info.tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
                if is_dict_object(arg.annotation):
                    names.add(arg.arg)
            if node.args.vararg and is_dict_object(node.args.vararg.annotation):
                names.add(node.args.vararg.arg)
            if node.args.kwarg and is_dict_object(node.args.kwarg.annotation):
                names.add(node.args.kwarg.arg)
            for child in ast.walk(node):
                if (
                    isinstance(child, ast.AnnAssign)
                    and isinstance(child.target, ast.Name)
                    and is_dict_object(child.annotation)
                ):
                    names.add(child.target.id)
    return names


def _object_dict_attribute_violations(info: SourceInfo) -> list[str]:
    """Reject object-typed record attribute access without banning mapping APIs."""

    allowed_mapping_methods = {"get", "items", "keys", "values", "copy", "update", "setdefault"}
    violations: list[str] = []

    def is_dict_object(annotation: ast.expr | None) -> bool:
        if not isinstance(annotation, ast.Subscript) or not isinstance(annotation.value, ast.Name):
            return False
        elements = annotation.slice.elts if isinstance(annotation.slice, ast.Tuple) else ()
        return (
            annotation.value.id == "dict"
            and len(elements) == 2
            and isinstance(elements[1], ast.Name)
            and elements[1].id == "object"
        )

    for function in (
        node for node in ast.walk(info.tree) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ):
        names = {
            arg.arg
            for arg in (*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs)
            if is_dict_object(arg.annotation)
        }
        for child in ast.walk(function):
            if (
                isinstance(child, ast.AnnAssign)
                and isinstance(child.target, ast.Name)
                and is_dict_object(child.annotation)
            ):
                names.add(child.target.id)
        for child in ast.walk(function):
            if (
                isinstance(child, ast.Attribute)
                and isinstance(child.value, ast.Name)
                and child.value.id in names
                and child.attr not in allowed_mapping_methods
            ):
                violations.append(
                    f"{info.path}:{child.lineno}: arbitrary attribute access on dict[str, object] value "
                    f"{child.value.id}.{child.attr}"
                )
    return violations


def _is_db_receiver(expression: ast.expr, known: set[str]) -> bool:
    if isinstance(expression, ast.Name):
        return expression.id in known or expression.id.lower() in {"db", "session", "connection", "conn", "uow"}
    if isinstance(expression, ast.Attribute):
        return _is_db_receiver(expression.value, known)
    if isinstance(expression, ast.Call):
        return isinstance(expression.func, ast.Name) and expression.func.id in known
    return False


def _annotation_names(annotation: ast.expr | None) -> set[str]:
    if isinstance(annotation, ast.Name):
        return {annotation.id}
    if isinstance(annotation, ast.Attribute):
        return _annotation_names(annotation.value)
    if isinstance(annotation, ast.Subscript):
        return _annotation_names(annotation.value) | _annotation_names(annotation.slice)
    if isinstance(annotation, ast.BinOp):
        return _annotation_names(annotation.left) | _annotation_names(annotation.right)
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        try:
            parsed = ast.parse(annotation.value, mode="eval").body
        except SyntaxError:
            return set()
        return _annotation_names(parsed)
    if isinstance(annotation, ast.Tuple | ast.List | ast.Set):
        names: set[str] = set()
        for item in annotation.elts:
            names.update(_annotation_names(item))
        return names
    return set()


def _import_alias_targets(info: SourceInfo, refs: list[ImportRef], index: DependencyIndex) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for ref in refs:
        targets = _target_module(info, ref, index)
        for alias, target in zip(ref.aliases, targets, strict=False):
            if alias != "*":
                bindings[alias] = target
    return bindings


def _api_database_violations(info: SourceInfo, refs: list[ImportRef], index: DependencyIndex) -> list[str]:
    if info.role != "api":
        return []
    violations: list[str] = []
    known: set[str] = {"db", "session", "connection", "conn", "uow"}
    alias_targets = _import_alias_targets(info, refs, index)
    db_names = {
        alias for alias, target in alias_targets.items() if any(_matches(target, root) for root in DB_IMPORT_ROOTS)
    }
    sql_names = {alias for alias, target in alias_targets.items() if _matches(target, "sqlalchemy")}
    dynamic_import_names = {"import_module"}
    for ref in refs:
        if ref.raw_module == "importlib":
            dynamic_import_names.update(
                alias for name, alias in zip(ref.names, ref.aliases, strict=False) if name == "import_module"
            )
    for node in ast.walk(info.tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
                annotation_names = _annotation_names(arg.annotation)
                if (
                    arg.arg.lower() in {"db", "session", "connection", "conn", "uow"}
                    or annotation_names & db_names
                ):
                    known.add(arg.arg)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            value_is_db = isinstance(node.value, ast.Name) and node.value.id in known
            if _annotation_names(node.annotation) & db_names or value_is_db:
                known.add(node.target.id)
        elif isinstance(node, ast.Assign):
            value_is_db = (
                isinstance(node.value, ast.Name)
                and node.value.id in known
                or isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id in db_names
            )
            if value_is_db:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        known.add(target.id)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in sql_names:
                violations.append(f"{info.path}:{node.lineno}: API directly calls SQLAlchemy {node.func.id}()")
            if isinstance(node.func, ast.Name) and node.func.id in dynamic_import_names:
                violations.append(f"{info.path}:{node.lineno}: dynamic import_module is not allowed")
            if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                violations.append(f"{info.path}:{node.lineno}: dynamic __import__ is not allowed")
            if isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
                violations.append(f"{info.path}:{node.lineno}: dynamic import_module is not allowed")
            if isinstance(node.func, ast.Attribute) and node.func.attr in DB_WRITE_METHODS | DB_READ_METHODS:
                if _is_db_receiver(node.func.value, known):
                    violations.append(f"{info.path}:{node.lineno}: API performs database call .{node.func.attr}()")
    return violations


def _check_source(
    source: str, relative_path: str, config: dict[str, object], index: DependencyIndex | None = None
) -> list[str]:
    info = _source_info(source, relative_path)
    normalized = _normalize_path(relative_path)
    if info is None:
        try:
            ast.parse(source, filename=normalized)
        except SyntaxError as error:
            return [f"{normalized}:{error.lineno}: syntax error: {error.msg}"]
        return [f"{normalized}: unable to parse source"]
    active_index = index or DependencyIndex([info])
    refs = _imports_from_tree(info)
    violations: list[str] = []

    for ref in refs:
        targets = _target_module(info, ref, active_index)
        orm_model_type_reference = _is_orm_model_type_reference(info, ref, targets, active_index)
        for target in targets:
            if not target:
                continue
            role, target_business_module, _target_layer = _role_for_target(target, active_index)
            if info.role == "shared" and target.startswith("app.") and role not in SHARED_ALLOWED_ROLES:
                violations.append(f"{normalized}:{ref.node.lineno}: shared has forbidden dependency {target}")
            if info.role == "platform" and target.startswith("app.") and role not in PLATFORM_ALLOWED_ROLES:
                violations.append(f"{normalized}:{ref.node.lineno}: platform has forbidden dependency {target}")
            if info.role in {"domain", "application"}:
                forbidden = APPLICATION_FORBIDDEN_ROOTS if info.role == "application" else CORE_FORBIDDEN_ROOTS
                if any(_matches(target, prefix) for prefix in forbidden):
                    violations.append(f"{normalized}:{ref.node.lineno}: {info.role} cannot import {target}")
                same_layer = target_business_module == info.business_module and role == info.role
                if role in {
                    "api",
                    "api_compat",
                    "application",
                    "bootstrap",
                    "infrastructure",
                    "legacy",
                    "models",
                    "platform",
                    "schemas",
                } and not same_layer or (
                    target_business_module is not None and target_business_module != info.business_module
                ):
                    if not (role == "public" and target_business_module != info.business_module):
                        violations.append(
                            f"{normalized}:{ref.node.lineno}: {info.role} has forbidden dependency {target}"
                        )
            if info.business_module and info.layer not in {"wiring", "api"}:
                if target_business_module and target_business_module != info.business_module:
                    if role == "api":
                        violations.append(f"{normalized}:{ref.node.lineno}: cross-module internal import {target}")
                    elif role in {"application", "domain", "infrastructure"}:
                        if not orm_model_type_reference and not _is_allowed_import(normalized, target, config):
                            violations.append(
                                f"{normalized}:{ref.node.lineno}: cross-module internal import {target}"
                            )
            if info.layer == "infrastructure" and _matches(target, "app.services"):
                if not _is_allowed_import(normalized, target, config):
                    violations.append(f"{normalized}:{ref.node.lineno}: infrastructure imports legacy service {target}")
            if info.role not in {"legacy", "models", "schemas"} and _matches(target, "app.services"):
                if not _is_allowed_import(normalized, target, config):
                    violations.append(
                        f"{normalized}:{ref.node.lineno}: production path imports legacy service {target}"
                    )
            if info.role == "public" and role in {"infrastructure", "models", "schemas", "legacy"}:
                violations.append(f"{normalized}:{ref.node.lineno}: public contract imports {target}")

    if info.role == "models":
        if any(isinstance(node, ast.ClassDef) for node in ast.walk(info.tree)):
            violations.append(f"{normalized}: central models may only re-export canonical module models")
        if any(_matches(target, "sqlalchemy") for ref in refs for target in _target_module(info, ref, active_index)):
            violations.append(f"{normalized}: central models may not import SQLAlchemy")

    if info.role in {"domain", "application", "public"}:
        if any(isinstance(node, ast.Name) and node.id == "Any" for node in ast.walk(info.tree)):
            violations.append(f"{normalized}: typing.Any is not allowed in module contracts")
        for ref in refs:
            if any(name == "Any" for name in ref.names):
                violations.append(f"{normalized}:{ref.node.lineno}: typing.Any is not allowed in module contracts")
        for token in ("# type: ignore", "# pyright: ignore", "ignore_errors", "service_locator"):
            if token in source:
                violations.append(f"{normalized}: forbidden escape hatch {token}")
        violations.extend(_object_dict_attribute_violations(info))

    dynamic_import_names = {"import_module"}
    for ref in refs:
        if ref.raw_module == "importlib":
            dynamic_import_names.update(
                alias for name, alias in zip(ref.names, ref.aliases, strict=False) if name == "import_module"
            )
    for node in ast.walk(info.tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                violations.append(f"{normalized}:{node.lineno}: dynamic __import__ is not allowed")
            if isinstance(node.func, ast.Name) and node.func.id in dynamic_import_names:
                violations.append(f"{normalized}:{node.lineno}: dynamic import_module is not allowed")
            if isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
                violations.append(f"{normalized}:{node.lineno}: dynamic import_module is not allowed")

    violations.extend(_api_database_violations(info, refs, active_index))
    return list(dict.fromkeys(violations))


def _graph(index: DependencyIndex) -> dict[str, set[str]]:
    graph = {module: set() for module in index.sources}
    for source in index.sources.values():
        for ref in _imports_from_tree(source):
            targets = index.targets(ref)
            if _is_orm_model_type_reference(source, ref, targets, index):
                continue
            graph[source.module].update(target for target in targets if target in index.sources)
    return graph


def _cycles(graph: dict[str, set[str]]) -> list[tuple[str, ...]]:
    counter = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[tuple[str, ...]] = []

    def visit(node: str) -> None:
        nonlocal counter
        indices[node] = counter
        lowlinks[node] = counter
        counter += 1
        stack.append(node)
        on_stack.add(node)
        for child in graph.get(node, set()):
            if child not in indices:
                visit(child)
                lowlinks[node] = min(lowlinks[node], lowlinks[child])
            elif child in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[child])
        if lowlinks[node] == indices[node]:
            component: list[str] = []
            while True:
                child = stack.pop()
                on_stack.remove(child)
                component.append(child)
                if child == node:
                    break
            if len(component) > 1 or node in graph.get(node, set()):
                components.append(tuple(sorted(component)))

    for node in graph:
        if node not in indices:
            visit(node)
    return sorted(components)


def _check_repository(config: dict[str, object]) -> list[str]:
    violations: list[str] = []
    modules = config.get("modules", [])
    layers = config.get("layers", [])
    required_files = config.get("required_files", [])
    if not isinstance(modules, list) or not isinstance(layers, list) or not isinstance(required_files, list):
        return ["backend-boundaries.json has invalid modules/layers/required_files"]
    for module in modules:
        module_root = APP_ROOT / "modules" / str(module)
        for layer in layers:
            path = module_root / str(layer)
            if not path.is_dir():
                violations.append(f"missing directory: {path.relative_to(ROOT).as_posix()}")
        for filename in required_files:
            path = module_root / str(filename)
            if not path.is_file():
                violations.append(f"missing file: {path.relative_to(ROOT).as_posix()}")
        api_files = [path for path in (module_root / "api").glob("*.py") if path.name != "__init__.py"]
        if not api_files:
            violations.append(f"empty API boundary: {module_root.relative_to(ROOT).as_posix()}/api")
        elif not any("APIRouter" in path.read_text(encoding="utf-8") for path in api_files):
            violations.append(
                f"API boundary has no router implementation: {module_root.relative_to(ROOT).as_posix()}/api"
            )

    index = _build_index()
    for source in index.sources.values():
        violations.extend(_check_source(source.source, source.path, config, index))
    for cycle in _cycles(_graph(index)):
        violations.append(f"project import cycle: {' -> '.join(cycle)}")
    return list(dict.fromkeys(violations))


def check_repository(config: dict[str, object]) -> list[str]:
    """Public repository-check entry point retained for orchestration scripts."""

    return _check_repository(config)


def self_test(config: dict[str, object]) -> int:
    index = _build_index()
    cases: list[tuple[str, str, str, bool, str]] = [
        (
            "positive shared application import",
            "from app.shared.actor import Actor\n\nclass UseCase:\n    pass\n",
            "app/modules/demo/application/use_case.py",
            False,
            "",
        ),
        (
            "positive cross-module public contract",
            "from app.modules.training.public import TrainingCasePort\n",
            "app/modules/learning/application/use_case.py",
            False,
            "",
        ),
        (
            "positive shared internal contract",
            "from app.shared.errors import AppError\n",
            "app/shared/value.py",
            False,
            "",
        ),
        (
            "positive platform config dependency",
            "from app.core.config import get_settings\n",
            "app/platform/example.py",
            False,
            "",
        ),
        (
            "positive API typed session without write",
            "from sqlalchemy.orm import Session as DbSession\n\ndef route(handle: DbSession):\n    return handle\n",
            "app/modules/demo/api/routes.py",
            False,
            "",
        ),
        (
            "relative application to infrastructure",
            "from ..infrastructure.repository import Repository\n",
            "app/modules/demo/application/use_case.py",
            True,
            "infrastructure",
        ),
        (
            "domain through app models export",
            "from app import models\n",
            "app/modules/demo/domain/policy.py",
            True,
            "app.models",
        ),
        (
            "domain through aliased model export",
            "from app.models import Problem as ModelProblem\n",
            "app/modules/demo/domain/policy.py",
            True,
            "app.modules.content.infrastructure.models",
        ),
        (
            "API untyped session commit",
            "def route(session):\n    session.commit()\n",
            "app/modules/demo/api/routes.py",
            True,
            "database call .commit",
        ),
        (
            "application platform transaction import",
            "from app.platform import transactions\n",
            "app/modules/demo/application/use_case.py",
            True,
            "app.platform",
        ),
        (
            "API aliased annotated session commit",
            (
                "from sqlalchemy.orm import Session as DbSession\n\n"
                "def route(handle: DbSession):\n"
                "    handle.commit()\n"
            ),
            "app/modules/demo/api/routes.py",
            True,
            "database call .commit",
        ),
        (
            "domain app core config import",
            "from app.core.config import settings\n",
            "app/modules/demo/domain/policy.py",
            True,
            "app.core.config",
        ),
        (
            "shared cross-module infrastructure import",
            "from app.modules.reports.infrastructure import repositories\n",
            "app/shared/report_reader.py",
            True,
            "shared has forbidden dependency",
        ),
        (
            "dynamic import alias",
            (
                "from importlib import import_module as load\n\n"
                "def load_reports():\n"
                "    return load('app.modules.reports.infrastructure.repositories')\n"
            ),
            "app/modules/demo/application/loader.py",
            True,
            "dynamic import_module",
        ),
        (
            "domain own application import",
            "from ..application import ports\n",
            "app/modules/demo/domain/policy.py",
            True,
            "application",
        ),
        (
            "type-only infrastructure import",
            (
                "from typing import TYPE_CHECKING\n\n"
                "if TYPE_CHECKING:\n"
                "    from ..infrastructure.repository import Repository\n"
            ),
            "app/modules/demo/application/use_case.py",
            True,
            "infrastructure",
        ),
    ]
    failed = False
    if _role_for_target("app.core.config", index)[0] != "platform":
        failed = True
        print("FAIL app.core source classification: expected platform")
    for name, source, path, should_fail, marker in cases:
        errors = _check_source(source, path, config, index)
        passed = any(marker in error for error in errors) if should_fail else not errors
        if not passed:
            failed = True
            print(f"FAIL {name}: {'; '.join(errors) or 'no violation'}")
        else:
            print(f"PASS {name}")

    empty_allowlist_config = {**config, "allowed_imports": []}
    api_probe_errors = _check_source(
        "from app.modules.training.api.schemas import CaseDraftModel\n",
        "app/modules/content/infrastructure/provider_probe.py",
        empty_allowlist_config,
        index,
    )
    api_probe_marker = "cross-module internal import"
    if not any(api_probe_marker in error for error in api_probe_errors):
        failed = True
        detail = "; ".join(api_probe_errors) or "no violation"
        print(f"FAIL infrastructure cross-module API import with empty allowlist: {detail}")
    else:
        print("PASS infrastructure cross-module API import with empty allowlist")

    for path in (
        "app/modules/content/infrastructure/public_probe.py",
        "app/modules/content/application/public_probe.py",
    ):
        public_probe_errors = _check_source(
            "from app.modules.training.public import TrainingCasePort\n",
            path,
            empty_allowlist_config,
            index,
        )
        if public_probe_errors:
            failed = True
            print(f"FAIL {path} cross-module public contract: {'; '.join(public_probe_errors)}")
        else:
            print(f"PASS {path} cross-module public contract with empty allowlist")

    graph = {"demo.a": {"demo.b"}, "demo.b": {"demo.a"}, "demo.c": set()}
    if not _cycles(graph):
        failed = True
        print("FAIL import-cycle detection")
    else:
        print("PASS import-cycle detection")
    if failed:
        print("backend-boundaries self-test: FAIL")
        return 1
    print("backend-boundaries self-test: PASS (positive, negative, alias, type-only, SQL, cycle probes)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if args.self_test:
        return self_test(config)
    violations = check_repository(config)
    if violations:
        print("backend-boundaries: FAIL")
        print("\n".join(violations))
        return 1
    print(
        "backend-boundaries: PASS "
        f"({len(config['modules'])} modules; layers={','.join(config['layers'])}; "
        "resolved imports + cycles + source-traced DB checks)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
