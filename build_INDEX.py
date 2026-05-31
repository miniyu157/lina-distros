#!/usr/bin/env python3

import hashlib
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DISTROS_DIR = SCRIPT_DIR / "distros"
VERSION = "v3.2"


def run_info(script: Path) -> dict | None:
    try:
        r = subprocess.run(
            ["bash", str(script), "info"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return None
        data = json.loads(r.stdout)
        if not isinstance(data, dict) or not data:
            return None
        return data
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None


def compute_file_hash(script: Path) -> str:
    return hashlib.sha256(script.read_bytes()).hexdigest()


def build_entries() -> list[dict]:
    entries = []
    for script in sorted(DISTROS_DIR.glob("*.sh")):
        info = run_info(script)
        if info is None:
            print(f"Warning: skipping invalid script: {script}", file=sys.stderr)
            continue
        entry: dict[str, object] = {
            "name": script.stem,
            "path": str(script.relative_to(SCRIPT_DIR)),
        }
        entry.update(info)
        entry["hash"] = compute_file_hash(script)
        entries.append(entry)
    return entries


def main() -> None:
    if "--version" in sys.argv:
        print(VERSION)
        return

    index = {
        "version": VERSION,
        "entries": build_entries(),
    }
    json.dump(index, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
