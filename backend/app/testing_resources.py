"""Owned, file-backed SQLite resources used by tests and local E2E runs.

This module deliberately has no application configuration imports.  Test
launchers can therefore claim an isolated resource *before* importing settings
or creating a SQLAlchemy engine.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

MARKER_NAME = ".medical-qa-owned-test-resource.json"
DATABASE_NAME = "app.sqlite3"


class ResourceOwnershipError(RuntimeError):
    """Raised when a cleanup request does not target a resource we created."""


@dataclass(frozen=True)
class ManagedDatabase:
    root: Path
    database_path: Path
    token: str

    @property
    def url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"


def create_managed_database(kind: str) -> ManagedDatabase:
    """Create a unique resource directly below the platform temporary folder."""
    if not kind.replace("-", "").replace("_", "").isidentifier():
        raise ValueError(f"Invalid test resource kind: {kind!r}")
    root = Path(tempfile.mkdtemp(prefix=f"medical-qa-{kind}-")).resolve(strict=True)
    if root.parent != Path(tempfile.gettempdir()).resolve(strict=True):
        raise ResourceOwnershipError("Test resource escaped the configured temporary directory")
    token = secrets.token_urlsafe(32)
    (root / MARKER_NAME).write_text(json.dumps({"kind": kind, "token": token}), encoding="utf-8")
    return ManagedDatabase(root=root, database_path=root / DATABASE_NAME, token=token)


def database_url_for(resource: ManagedDatabase) -> str:
    return resource.url


def _read_marker(root: Path) -> dict[str, str]:
    marker = root / MARKER_NAME
    if _is_link_or_reparse(marker) or not marker.is_file():
        raise ResourceOwnershipError("Missing or linked test resource ownership marker")
    try:
        content = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ResourceOwnershipError("Unreadable test resource ownership marker") from error
    if not isinstance(content, dict) or not isinstance(content.get("token"), str) or len(content["token"]) < 32:
        raise ResourceOwnershipError("Invalid test resource ownership marker")
    return content


def _is_link_or_reparse(path: Path) -> bool:
    """Detect Unix links and Windows symlinks, junctions and other reparse points."""
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return True
    is_junction = getattr(path, "is_junction", lambda: False)
    reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(attributes & reparse_point) or is_junction()


def assert_owned_resource(resource: ManagedDatabase) -> None:
    """Validate containment, canonical paths, ownership and link boundaries."""
    temp_root = Path(tempfile.gettempdir()).resolve(strict=True)
    root = resource.root.absolute()
    if _is_link_or_reparse(root) or not root.is_dir():
        raise ResourceOwnershipError("Test resource root is missing or linked")
    resolved_root = root.resolve(strict=True)
    if resolved_root.parent != temp_root or resolved_root != root:
        raise ResourceOwnershipError("Test resource root is outside the temporary directory")
    database_path = resource.database_path.absolute()
    if database_path.parent != root or database_path.name != DATABASE_NAME:
        raise ResourceOwnershipError("Unexpected test database path")
    # is_symlink() also detects a dangling link, for which exists() is false.
    if database_path.is_symlink() or (database_path.exists() and _is_link_or_reparse(database_path)):
        raise ResourceOwnershipError("Test database path must not be a link")
    marker = _read_marker(root)
    if marker["token"] != resource.token:
        raise ResourceOwnershipError("Test resource ownership token does not match")


def cleanup_managed_database(resource: ManagedDatabase) -> None:
    """Remove only a resource with the exact marker created by this launcher."""
    assert_owned_resource(resource)
    pending = [resource.root]
    while pending:
        current = pending.pop()
        try:
            entries = list(os.scandir(current))
        except OSError as error:
            raise ResourceOwnershipError("Unable to inspect the owned test resource") from error
        for entry in entries:
            path = Path(entry.path)
            if _is_link_or_reparse(path):
                raise ResourceOwnershipError("Refusing to clean a resource containing a link or reparse point")
            if entry.is_dir(follow_symlinks=False):
                pending.append(path)
    shutil.rmtree(resource.root)


def managed_database_from_environment() -> ManagedDatabase:
    """Reconstruct a launcher-owned resource for defensive E2E cleanup."""
    root_raw = os.environ["TEST_RESOURCE_DIR"]
    token = os.environ["TEST_RESOURCE_TOKEN"]
    root = Path(root_raw).absolute()
    resource = ManagedDatabase(root=root, database_path=root / DATABASE_NAME, token=token)
    assert_owned_resource(resource)
    return resource
