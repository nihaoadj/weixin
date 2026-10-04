"""Regression coverage for the test launcher ownership contract (DB-01 to DB-09)."""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import Request, urlopen

import pytest
from sqlalchemy import text

from app.testing_resources import (
    ManagedDatabase,
    ResourceOwnershipError,
    assert_owned_resource,
    cleanup_managed_database,
    create_managed_database,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROBE = "tests/safety_probe.py"


def run_probe(tmp_path: Path, inherited_database_url: str, *, optimized: bool = False) -> str:
    output = tmp_path / "probe-url.txt"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = inherited_database_url
    environment["SAFETY_PROBE_OUTPUT"] = str(output)
    result = subprocess.run(
        [sys.executable, *(["-O"] if optimized else []), "-m", "pytest", PROBE, "-q"],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return output.read_text(encoding="utf-8")


def start_held_probe(directory: Path, name: str) -> tuple[subprocess.Popen[str], Path, Path]:
    output = directory / f"{name}-url.txt"
    release = directory / f"{name}-release"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = "postgresql://unreachable.invalid/never-connect"
    environment["SAFETY_PROBE_OUTPUT"] = str(output)
    environment["SAFETY_PROBE_RELEASE"] = str(release)
    process = subprocess.Popen(
        [sys.executable, "-m", "pytest", PROBE, "-q"],
        cwd=BACKEND_ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.monotonic() + 30
    while not output.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert output.exists(), process.communicate(timeout=5)[0]
    return process, output, release


def unused_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def start_e2e_server(directory: Path, name: str) -> tuple[subprocess.Popen[bytes], Path, Path, Path, str]:
    """Start the real E2E launcher and wait for its declared owned resource."""
    port = unused_loopback_port()
    h5_port = unused_loopback_port()
    log_path = directory / f"{name}.log"
    shutdown_path = directory / f"{name}.shutdown"
    log = log_path.open("wb")
    environment = os.environ.copy()
    environment.update(
        {
            "E2E_PORT": str(port),
            "E2E_CORS_ORIGIN": f"http://127.0.0.1:{h5_port}",
            "E2E_SHUTDOWN_FILE": str(shutdown_path),
            "PYTHONUNBUFFERED": "1",
        }
    )
    process = subprocess.Popen(
        [sys.executable, "scripts/run_e2e_server.py"],
        cwd=BACKEND_ROOT,
        env=environment,
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    deadline = time.monotonic() + 60
    health_url = f"http://127.0.0.1:{port}/health"
    while time.monotonic() < deadline:
        try:
            with urlopen(health_url, timeout=1) as response:  # noqa: S310 - loopback URL built above
                if response.status == 200:
                    break
        except OSError:
            if process.poll() is not None:
                break
            time.sleep(0.1)
    log.close()
    content = log_path.read_text(encoding="utf-8", errors="replace")
    resource_lines = [line for line in content.splitlines() if line.startswith("E2E database resource: ")]
    assert process.poll() is None and resource_lines, content
    return (
        process,
        Path(resource_lines[-1].removeprefix("E2E database resource: ")),
        log_path,
        shutdown_path,
        f"http://127.0.0.1:{h5_port}",
    )


def stop_e2e_server(process: subprocess.Popen[bytes], log_path: Path, shutdown_path: Path) -> None:
    shutdown_path.touch()
    try:
        exit_code = process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.terminate()
        pytest.fail(f"E2E server did not shut down cleanly:\n{log_path.read_text(encoding='utf-8', errors='replace')}")
    assert exit_code == 0, log_path.read_text(encoding="utf-8", errors="replace")


def test_inherited_development_sqlite_database_is_never_opened() -> None:
    """DB-01: a child pytest process must ignore an inherited developer URL."""
    with TemporaryDirectory(prefix="medical-qa-db01-") as directory:
        directory_path = Path(directory)
        development_db = directory_path / "development.db"
        connection = sqlite3.connect(development_db)
        try:
            connection.execute("CREATE TABLE sentinel (value TEXT NOT NULL)")
            connection.execute("INSERT INTO sentinel VALUES ('do-not-touch')")
            connection.commit()
        finally:
            connection.close()
        original_bytes = development_db.read_bytes()

        selected_url = run_probe(directory_path, f"sqlite:///{development_db.as_posix()}")

        assert selected_url != f"sqlite:///{development_db.as_posix()}"
        assert development_db.read_bytes() == original_bytes
        connection = sqlite3.connect(development_db)
        try:
            assert connection.execute("SELECT value FROM sentinel").fetchone() == ("do-not-touch",)
        finally:
            connection.close()


def test_external_database_url_is_replaced_before_application_import() -> None:
    """DB-02: an unreachable external URL cannot be connected by a test import."""
    with TemporaryDirectory(prefix="medical-qa-db02-") as directory:
        selected_url = run_probe(Path(directory), "postgresql://unreachable.invalid/never-connect")
        assert selected_url.startswith("sqlite:///")
        assert "unreachable.invalid" not in selected_url


def test_database_binding_guard_survives_optimized_python() -> None:
    """DB-02: isolation must not depend on assertions removed by ``python -O``."""
    with TemporaryDirectory(prefix="medical-qa-db02-optimized-") as directory:
        selected_url = run_probe(
            Path(directory),
            "postgresql://unreachable.invalid/never-connect",
            optimized=True,
        )
        assert selected_url.startswith("sqlite:///")
        assert "unreachable.invalid" not in selected_url


def test_cleanup_rejects_outside_paths_and_links() -> None:
    """DB-03: cleanup validates canonical containment and never follows a link."""
    resource = create_managed_database("safety")
    with TemporaryDirectory(prefix="medical-qa-db03-") as directory:
        outside = Path(directory) / "outside.db"
        outside.write_text("sentinel", encoding="utf-8")
        escaped = ManagedDatabase(resource.root, outside, resource.token)
        with pytest.raises(ResourceOwnershipError):
            cleanup_managed_database(escaped)
        assert outside.read_text(encoding="utf-8") == "sentinel"

        link = resource.root / "linked-outside"
        try:
            link.symlink_to(outside)
        except OSError:
            junction = resource.root / "junction-outside"
            command = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(junction), str(outside.parent)],
                capture_output=True,
                text=True,
                check=False,
            )
            if command.returncode != 0:
                pytest.fail(f"Cannot create a symlink or junction for DB-03: {command.stderr or command.stdout}")
            with pytest.raises(ResourceOwnershipError):
                cleanup_managed_database(resource)
            assert outside.read_text(encoding="utf-8") == "sentinel"
            junction.rmdir()
            cleanup_managed_database(resource)
        else:
            with pytest.raises(ResourceOwnershipError):
                cleanup_managed_database(resource)
            assert outside.read_text(encoding="utf-8") == "sentinel"
            link.unlink()
            cleanup_managed_database(resource)


def test_schema_creation_rejects_a_dangling_database_symlink() -> None:
    """DB-03 companion: a dangling database link is never treated as a new local file."""
    resource = create_managed_database("dangling")
    outside_root = Path(tempfile.mkdtemp(prefix=f"medical-qa-outside-{resource.token[:12]}-"))
    outside = outside_root / "missing.db"
    junction = False
    symlink = False
    try:
        try:
            resource.database_path.symlink_to(outside)
            symlink = True
        except OSError:
            command = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(resource.database_path), str(outside_root)],
                capture_output=True,
                text=True,
                check=False,
            )
            if command.returncode != 0:
                pytest.fail(
                    f"Cannot create a dangling symlink or junction for DB-03: {command.stderr or command.stdout}"
                )
            junction = True
        with pytest.raises(ResourceOwnershipError):
            assert_owned_resource(resource)
    finally:
        if symlink:
            resource.database_path.unlink()
        elif junction:
            resource.database_path.rmdir()
        cleanup_managed_database(resource)
        outside_root.rmdir()
    assert not outside.exists()


def test_cleanup_rejects_a_non_object_ownership_marker() -> None:
    """DB-03 companion: malformed marker JSON never passes an ownership check."""
    resource = create_managed_database("marker")
    marker_path = resource.root / ".medical-qa-owned-test-resource.json"
    try:
        marker_path.write_text("[]", encoding="utf-8")
        with pytest.raises(ResourceOwnershipError):
            assert_owned_resource(resource)
    finally:
        marker_path.write_text(json.dumps({"kind": "marker", "token": resource.token}), encoding="utf-8")
        cleanup_managed_database(resource)


def test_parallel_pytest_launchers_receive_distinct_resources() -> None:
    """DB-04: two live pytest subprocesses each retain an independent database."""
    with TemporaryDirectory(prefix="medical-qa-db04-") as directory:
        root = Path(directory)
        first, first_output, first_release = start_held_probe(root, "first")
        second, second_output, second_release = start_held_probe(root, "second")
        try:
            assert first.poll() is None and second.poll() is None
            assert first_output.read_text(encoding="utf-8") != second_output.read_text(encoding="utf-8")
        finally:
            first_release.touch()
            second_release.touch()
            assert first.wait(timeout=30) == 0
            assert second.wait(timeout=30) == 0


def test_parallel_e2e_servers_use_distinct_databases_and_ports() -> None:
    """DB-05: two real E2E servers run together without sharing resources."""
    with TemporaryDirectory(prefix="medical-qa-db05-") as directory:
        root = Path(directory)
        first, first_resource, first_log, first_shutdown, _first_origin = start_e2e_server(root, "first")
        second, second_resource, second_log, second_shutdown, _second_origin = start_e2e_server(root, "second")
        try:
            assert first_resource != second_resource
            assert (first_resource / "app.sqlite3").exists()
            assert (second_resource / "app.sqlite3").exists()
        finally:
            stop_e2e_server(first, first_log, first_shutdown)
            stop_e2e_server(second, second_log, second_shutdown)
        assert not first_resource.exists()
        assert not second_resource.exists()


def test_e2e_port_collision_fails_without_killing_existing_listener() -> None:
    """DB-05: a requested occupied API port is a clear startup failure."""
    with TemporaryDirectory(prefix="medical-qa-e2e-port-") as directory:
        log_path = Path(directory) / "collision.log"
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        occupied_port = int(listener.getsockname()[1])
        environment = os.environ.copy()
        environment.update(
            {
                "E2E_PORT": str(occupied_port),
                "E2E_CORS_ORIGIN": f"http://127.0.0.1:{unused_loopback_port()}",
                "PYTHONUNBUFFERED": "1",
            }
        )
        with log_path.open("wb") as log:
            process = subprocess.Popen(
                [sys.executable, "scripts/run_e2e_server.py"],
                cwd=BACKEND_ROOT,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        try:
            exit_code = process.wait(timeout=60)
            assert exit_code != 0, log_path.read_text(encoding="utf-8", errors="replace")
            assert listener.fileno() != -1
        finally:
            listener.close()


def test_e2e_launcher_seeds_api_data_and_matches_cors_origin() -> None:
    """DB-05/DB-09: exercise the real seeded E2E server over loopback HTTP."""
    with TemporaryDirectory(prefix="medical-qa-e2e-flow-") as directory:
        process, resource_root, log_path, shutdown_path, origin = start_e2e_server(Path(directory), "flow")
        base_url = next(
            line.removeprefix("E2E API URL: ")
            for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.startswith("E2E API URL: ")
        )
        try:
            preflight = Request(
                f"{base_url}/health",
                method="OPTIONS",
                headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
            )
            with urlopen(preflight, timeout=5) as response:  # noqa: S310 - loopback URL from child log
                assert response.headers["Access-Control-Allow-Origin"] == origin

            login_request = Request(
                f"{base_url}/auth/demo-login",
                data=json.dumps(
                    {"role": "teacher", "external_id": "demo_teacher", "nickname": "teacher", "avatar_url": ""}
                ).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(login_request, timeout=5) as response:  # noqa: S310 - loopback URL from child log
                login_body = json.loads(response.read())
            token = login_body["access_token"]
            problems_request = Request(
                f"{base_url}/problems",
                headers={"Authorization": f"Bearer {token}"},
            )
            with urlopen(problems_request, timeout=5) as response:  # noqa: S310 - loopback URL from child log
                problems = json.loads(response.read())
            # The retained open question stays in the fixture database, while
            # the active content API now exposes only its six guided cases.
            assert len(problems) == 6
            assert all(item["content_type"] == "guided_case" for item in problems)
            assert any(item["slug"] == "pathology-demo-pending-v2" for item in problems)
            assert resource_root.joinpath("app.sqlite3").exists()
            database_uri = f"file:{resource_root.joinpath('app.sqlite3').as_posix()}?mode=ro"
            with closing(sqlite3.connect(database_uri, uri=True)) as seeded:
                assert seeded.execute("SELECT COUNT(*) FROM problems").fetchone()[0] == 7
        finally:
            stop_e2e_server(process, log_path, shutdown_path)
        assert not resource_root.exists()


def test_managed_client_supports_commits_and_lifespan(client, db) -> None:
    """DB-06: a context-managed TestClient and application commit share one DB."""
    response = client.post(
        "/auth/demo-login",
        json={"role": "student", "external_id": "fixture-commit", "nickname": "fixture", "avatar_url": ""},
    )
    assert response.status_code == 200
    assert db.execute(text("SELECT COUNT(*) FROM users")).scalar_one() == 1


def test_forced_e2e_interruption_leaves_only_its_owned_resource() -> None:
    """DB-08: a forced child interruption preserves only its own diagnostic files."""
    with TemporaryDirectory(prefix="medical-qa-db08-") as directory:
        process, resource_root, log_path, _shutdown_path, _origin = start_e2e_server(Path(directory), "interrupted")
        process.terminate()
        assert process.wait(timeout=30) != 0
        assert resource_root.exists()
        marker = json.loads((resource_root / ".medical-qa-owned-test-resource.json").read_text(encoding="utf-8"))
        resource = ManagedDatabase(resource_root, resource_root / "app.sqlite3", marker["token"])
        try:
            assert resource.database_path.exists()
            assert "E2E database resource:" in log_path.read_text(encoding="utf-8", errors="replace")
        finally:
            cleanup_managed_database(resource)
        assert not resource_root.exists()


def test_failed_cleanup_never_expands_to_a_similarly_named_resource() -> None:
    """DB-08 companion: a bad token cannot clean a resource owned by another run."""
    resource = create_managed_database("interrupted")
    resource.database_path.write_text("test data", encoding="utf-8")
    wrong_owner = ManagedDatabase(resource.root, resource.database_path, "x" * 43)
    try:
        with pytest.raises(ResourceOwnershipError):
            cleanup_managed_database(wrong_owner)
        assert resource.database_path.read_text(encoding="utf-8") == "test data"
    finally:
        cleanup_managed_database(resource)


def test_nonlocal_network_is_blocked_without_credentials() -> None:
    """DB-09: the global test guard prevents accidental provider requests."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        with pytest.raises(RuntimeError, match="Blocked non-local network access"):
            connection.connect(("203.0.113.1", 443))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        with pytest.raises(RuntimeError, match="Blocked non-local network access"):
            connection.connect_ex(("203.0.113.1", 443))
