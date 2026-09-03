"""Run the strict type gate over T04 domain/application cores."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def targets() -> list[str]:
    paths: list[str] = []
    for module_root in sorted(
        path for path in (ROOT / "app" / "modules").iterdir() if path.is_dir() and not path.name.startswith("__")
    ):
        for layer in ("domain", "application"):
            paths.append(str(module_root / layer))
        paths.append(str(module_root / "public.py"))
    paths.append(str(ROOT / "app" / "shared"))
    return paths


def negative_probe() -> int:
    source = """from app.modules.training.public import TrainingCasePort
from app.shared.actor import Actor


def invalid_contract(port: TrainingCasePort, actor: Actor) -> None:
    port.missing_method(actor)
    port.start(actor, \"not-an-int\", None, 1)
"""
    with tempfile.TemporaryDirectory(prefix="t04-mypy-negative-") as directory:
        probe = Path(directory) / "negative_contract.py"
        probe.write_text(source, encoding="utf-8")
        command = [
            sys.executable,
            "-m",
            "mypy",
            "--config-file",
            str(ROOT / "mypy.ini"),
            "--follow-imports",
            "normal",
            "--no-error-summary",
            "--show-error-codes",
            str(probe),
        ]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    output = f"{result.stdout}\n{result.stderr}"
    missing_method_rejected = "has no attribute \"missing_method\"" in output
    bad_argument_rejected = "Argument 2 to \"start\"" in output and "incompatible type \"str\"" in output
    if result.returncode == 0 or not (missing_method_rejected and bad_argument_rejected):
        print("type-check negative probe: FAIL")
        print(output.strip())
        return 1
    print("type-check negative probe: PASS (missing method and argument mismatch rejected)")
    return 0


def main() -> int:
    if "--negative" in sys.argv[1:]:
        return negative_probe()
    command = [sys.executable, "-m", "mypy", "--config-file", str(ROOT / "mypy.ini"), *targets()]
    return subprocess.run(command, cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
