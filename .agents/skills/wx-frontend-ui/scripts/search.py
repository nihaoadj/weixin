"""Project-local, read-only adapter for the pinned UI/UX Pro Max core.

Original adapter, 2026-09-12. Upstream core and datasets remain unchanged.
"""

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "pro-max"
DOMAINS = ("product", "style", "color", "typography", "ux", "chart", "icons")


def verify_sources():
    manifest = json.loads((VENDOR / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        # Normalize checkout newlines, retaining the upstream logical UTF-8 text.
        content = (VENDOR / entry["path"]).read_text(encoding="utf-8").encode("utf-8")
        digest = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        if digest != entry["git_blob_sha"]:
            raise ValueError(f"Pinned source mismatch: {entry['path']}")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--domain", choices=DOMAINS)
    mode.add_argument("--stack", choices=("vue",))
    parser.add_argument("-n", type=int, choices=range(1, 21), default=3)
    parser.add_argument("--verify-sources", action="store_true")
    args = parser.parse_args()
    if not args.verify_sources and (not args.query or not args.query.strip() or not (args.domain or args.stack)):
        parser.error("Supply a nonempty query and --domain or --stack")
    try:
        manifest = verify_sources()
        if args.verify_sources:
            print(json.dumps({"verified_files": len(manifest["files"]), "commit": manifest["commit"]}))
            return 0
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location("pro_max_core", VENDOR / "scripts" / "core.py")
        core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(core)
        result = (core.search_stack(args.query, args.stack, args.n, diagnostics=True)
                  if args.stack else core.search(args.query, args.domain, args.n, diagnostics=True))
        result["source_commit"] = manifest["commit"]
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 1 if "error" in result else 0
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
