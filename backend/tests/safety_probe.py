"""A deliberately explicit pytest target used by database-isolation subprocess tests."""

import os
from pathlib import Path
from time import sleep


def test_probe_uses_the_pytest_owned_database() -> None:
    from app.db import engine

    output = Path(os.environ["SAFETY_PROBE_OUTPUT"])
    output.write_text(str(engine.url), encoding="utf-8")
    release_file = os.environ.get("SAFETY_PROBE_RELEASE")
    if release_file:
        release = Path(release_file)
        while not release.exists():
            sleep(0.05)
