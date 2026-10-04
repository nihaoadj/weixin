import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest


@pytest.mark.parametrize("script_name", ["rebuild_t43_reports.py", "transition_t43_packages.py"])
def test_report_rebuild_cli_always_returns_retired_flow_without_creating_database(script_name: str) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / script_name
    resource_dir = Path(os.environ["TEST_RESOURCE_DIR"])
    token = uuid4().hex
    database = resource_dir / f"t43-retired-{token}.sqlite"
    backup = resource_dir / f"t43-retired-backup-{token}.sqlite"
    argument_sets = (
        [],
        ["--database", str(database)],
        ["--database", str(database), "--apply", "--confirm-development", "--backup", str(backup)],
        ["--help"],
    )

    for arguments in argument_sets:
        result = subprocess.run(
            [sys.executable, str(script), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode != 0
        assert "RETIRED_FLOW" in result.stderr
        assert not database.exists()
        assert not backup.exists()
