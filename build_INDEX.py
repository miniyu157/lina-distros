#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VERSION = "v5"


def validate_path(path: str) -> Path:
    """Validate a directory argument."""
    if path in frozenset({".", ".."}):
        print(f"error: reserved name: '{path}'", file=sys.stderr)
        sys.exit(1)
    if "/" in path or "\\" in path:
        print(f"error: path separators not allowed: '{path}'", file=sys.stderr)
        sys.exit(1)

    cwd = Path.cwd()
    resolved = (cwd / path).resolve()

    try:
        resolved.relative_to(cwd)
    except ValueError:
        print(f"error: '{path}' resolves outside current directory", file=sys.stderr)
        sys.exit(1)

    if not resolved.is_dir():
        print(f"error: directory not found: {path}", file=sys.stderr)
        sys.exit(1)

    return resolved


def iter_executables(distros_dir: Path):
    """Yield executable files from a directory."""
    for p in sorted(distros_dir.iterdir()):
        if p.is_file() and not p.name.startswith(".") and os.access(p, os.X_OK):
            yield p


def run_json(script: Path, subcommand: str, max_retries: int = 3) -> dict | None:
    """Run an applet subcommand and return parsed JSON. Retries on failure with exponential backoff."""
    for attempt in range(max_retries):
        try:
            r = subprocess.run([str(script), subcommand], capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                if attempt < max_retries - 1:
                    delay = 2**attempt
                    print(
                        f"warning: {script} {subcommand} exited with {r.returncode}, retrying in {delay}s...",
                        file=sys.stderr,
                    )
                    time.sleep(delay)
                    continue
                return None
            data = json.loads(r.stdout)
            if not isinstance(data, dict) or not data:
                if attempt < max_retries - 1:
                    delay = 2**attempt
                    print(
                        f"warning: {script} {subcommand} returned invalid JSON object, retrying in {delay}s...",
                        file=sys.stderr,
                    )
                    time.sleep(delay)
                    continue
                return None
            return data
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
            if attempt < max_retries - 1:
                delay = 2**attempt
                print(
                    f"warning: {script} {subcommand} attempt {attempt+1}/{max_retries} failed ({e}), retrying in {delay}s...",
                    file=sys.stderr,
                )
                time.sleep(delay)
                continue
            print(
                f"warning: {script} {subcommand} failed after {max_retries} attempts",
                file=sys.stderr,
            )
            return None


def compute_file_hash(script: Path) -> str:
    """Return the SHA256 hex digest of a file."""
    return hashlib.sha256(script.read_bytes()).hexdigest()


def build_entries(dirs: list[Path]) -> list[dict]:
    """Run info and options on each applet and assemble INDEX entries. Skip failed applets."""
    entries: list[dict] = []
    for d in dirs:
        for script in iter_executables(d):
            info_data = run_json(script, "info")
            if info_data is None:
                print(f"warning: skipping applet (info failed): {script}", file=sys.stderr)
                continue

            options_data = run_json(script, "options")
            if options_data is None:
                print(f"warning: skipping applet (options failed): {script}", file=sys.stderr)
                continue

            entry: dict[str, object] = {}
            entry.update(info_data)
            file_hash = compute_file_hash(script)
            entry["applet"] = {
                "file": str(script.relative_to(SCRIPT_DIR)),
                "hash": file_hash[:7],
                "options": options_data,
            }
            entries.append(entry)
    return entries


def _is_primitive_list(obj: object) -> bool:
    """True if obj is a list of scalar values (no nested dicts/lists)."""
    return isinstance(obj, list) and all(not isinstance(item, (dict, list)) for item in obj)


def _format_json(obj: object, indent: int = 0) -> str:
    """Custom JSON formatter: primitive arrays stay on a single compact line."""
    prefix = " " * indent
    if _is_primitive_list(obj):
        items = ", ".join(json.dumps(item, ensure_ascii=False) for item in obj)
        return f"[{items}]"
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        lines = []
        for key, value in obj.items():
            val_str = _format_json(value, indent + 2)
            lines.append(f"{prefix}  {json.dumps(key, ensure_ascii=False)}: {val_str}")
        return "{\n" + ",\n".join(lines) + f"\n{prefix}}}"
    if isinstance(obj, list):
        if not obj:
            return "[]"
        lines = []
        for item in obj:
            lines.append(f"{prefix}  {_format_json(item, indent + 2)}")
        return "[\n" + ",\n".join(lines) + f"\n{prefix}]"
    return json.dumps(obj, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Scan distro applet scripts and assemble an INDEX.\n"
            f"Calls each applet's info/options subcommands per the {VERSION} spec.\n"
            "Prints the assembled JSON to stdout."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("dirs", nargs="+", metavar="dir", help="distro subdirectories to scan (relative to cwd)")
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args()

    # Validate dirs
    dirs = [validate_path(n) for n in args.dirs]

    index = {
        "version": VERSION,
        "entries": build_entries(dirs),
    }
    sys.stdout.write(_format_json(index) + "\n")


if __name__ == "__main__":
    main()
