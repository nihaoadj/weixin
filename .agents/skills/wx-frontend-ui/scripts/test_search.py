"""Behavior checks for retrieval and failure handling; no application changes."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def invoke(*args, root=ROOT, cwd=None):
    return subprocess.run([sys.executable, str(root / "scripts/search.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")


class RetrievalTests(unittest.TestCase):
    def test_provenance(self):
        result = invoke("--verify-sources")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["verified_files"], 9)

    def test_domains_and_vue_from_another_directory(self):
        cases = [("product", "education learning"), ("style", "minimalism"),
                 ("color", "education"), ("typography", "readable"),
                 ("ux", "error summary validation"), ("chart", "trend time series"),
                 ("icons", "magnifying glass search"), ("vue", "computed reactive")]
        with tempfile.TemporaryDirectory() as temp:
            for domain, query in cases:
                with self.subTest(domain=domain):
                    result = invoke(query, "--stack" if domain == "vue" else "--domain", domain, cwd=temp)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    data = json.loads(result.stdout)
                    self.assertGreater(data["count"], 0, data)
                    self.assertLessEqual(data["count"], 3)
                    self.assertTrue(data["results"])

    def test_specific_outcomes(self):
        error = json.loads(invoke("error summary validation", "--domain", "ux", "-n", "1").stdout)
        self.assertEqual(error["results"][0]["Issue"], "Focusable Error Summary")
        vue = json.loads(invoke("computed reactive", "--stack", "vue", "-n", "1").stdout)
        self.assertEqual(vue["results"][0]["Guideline"], "Use computed for derived state")
        icon = json.loads(invoke("magnifying glass search", "--domain", "icons", "-n", "1").stdout)
        self.assertEqual(icon["results"][0]["Icon Name"], "magnifying-glass")

    def test_unmatched_query_is_not_fabricated(self):
        result = invoke("zzqvxxnonexistent", "--domain", "ux")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["results"], [])

    def test_invalid_options(self):
        for args in [("x", "--domain", "react"), ("x", "--stack", "nextjs"),
                     ("x", "--domain", "ux", "-n", "0"), (" ", "--domain", "ux"),
                     ("x", "--design-system")]:
            self.assertEqual(invoke(*args).returncode, 2)

    def test_corrupt_or_missing_data_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp) / "skill"
            shutil.copytree(ROOT, copy)
            target = copy / "vendor/pro-max/data/ux-guidelines.csv"
            with target.open("a", encoding="utf-8") as stream:
                stream.write("corruption")
            result = invoke("focus", "--domain", "ux", root=copy)
            self.assertEqual(result.returncode, 1)
            self.assertIn("mismatch", json.loads(result.stderr)["error"])
            target.unlink()
            result = invoke("focus", "--domain", "ux", root=copy)
            self.assertEqual(result.returncode, 1)
            self.assertIn("error", json.loads(result.stderr))


if __name__ == "__main__":
    unittest.main()
