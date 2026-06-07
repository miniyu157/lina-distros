#!/usr/bin/env python3
"""Compare old and new INDEX, print a multi-line commit message to stdout."""
import json
import sys


def base_name(full_name: str) -> str:
    """Strip hash suffix: 'archlinux.fdf02e3' → 'archlinux'."""
    parts = full_name.rsplit(".", 1)
    if len(parts) == 2 and len(parts[1]) == 7 and all(c in "0123456789abcdef" for c in parts[1]):
        return parts[0]
    return full_name


def set_diff(old_set: set[str], new_set: set[str]) -> str:
    """Format set difference: '+a, +b, -c, -d'."""
    parts: list[str] = []
    for item in sorted(new_set - old_set):
        parts.append(f"+{item}")
    for item in sorted(old_set - new_set):
        parts.append(f"-{item}")
    return ", ".join(parts)


def field_diff(label: str, old_set: set[str], new_set: set[str], indent: int = 2) -> str | None:
    """Return a diff line if sets differ, or None."""
    if old_set == new_set:
        return None
    prefix = " " * indent
    return f"{prefix}{label}: {set_diff(old_set, new_set)}"


def block_entry(filepath: str, old: dict | None, new: dict | None) -> str:
    """Build one distro's change block."""
    lines: list[str] = [f"{filepath}"]

    if new is not None:
        lines.append(f"  name:     {base_name(new['name'])}")
    if old is not None and new is None:
        lines.append(f"  name:     {base_name(old['name'])}")

    new_opts = new.get("exec", {}).get("options", {}) if new else {}
    old_opts = old.get("exec", {}).get("options", {}) if old else {}

    # desc
    new_desc = new.get("desc", "") if new else ""
    old_desc = old.get("desc", "") if old else ""
    if old is None:
        lines.append(f"  desc:     {new_desc}")
    elif new_desc != old_desc:
        lines.append(f"  desc:     {old_desc} → {new_desc}")

    # versions / archs / mirrors — only show if changed
    for key, label in [("versions", "versions"), ("archs", "archs"), ("mirrors", "mirrors")]:
        diff_line = field_diff(label, set(old_opts.get(key, [])), set(new_opts.get(key, [])))
        if diff_line:
            lines.append(diff_line)

    # script hash
    old_name = old.get("name", "") if old else ""
    new_name = new.get("name", "") if new else ""
    if old and new and old_name != new_name:
        _, old_hash = old_name.rsplit(".", 1) if "." in old_name else ("", old_name)
        _, new_hash = new_name.rsplit(".", 1) if "." in new_name else ("", new_name)
        lines.append(f"  hash:     {old_hash} → {new_hash}")
    elif old is None:
        _, h = new_name.rsplit(".", 1) if "." in new_name else ("", new_name)
        lines.append(f"  hash:     {h}")

    return "\n".join(lines)


def has_changes(old: dict, new: dict) -> bool:
    """True if any field differs between old and new entry."""
    if old.get("name") != new.get("name"):
        return True
    if old.get("desc") != new.get("desc"):
        return True
    o = old.get("exec", {}).get("options", {})
    n = new.get("exec", {}).get("options", {})
    for key in ("versions", "archs", "mirrors"):
        if o.get(key) != n.get(key):
            return True
    return False


def main() -> None:
    try:
        with open("INDEX") as f:
            old = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("auto: update INDEX (initial build)")
        sys.exit(0)

    with open("INDEX.new") as f:
        new = json.load(f)

    old_map = {e["exec"]["file"]: e for e in old.get("entries", [])}
    new_map = {e["exec"]["file"]: e for e in new.get("entries", [])}

    changed: list[str] = []   # base names for subject line
    blocks: list[str] = []    # change detail blocks

    for filepath, new_entry in new_map.items():
        old_entry = old_map.get(filepath)
        if old_entry is None:
            changed.append(base_name(new_entry["name"]))
            blocks.append(block_entry(filepath, None, new_entry))
        elif has_changes(old_entry, new_entry):
            changed.append(base_name(new_entry["name"]))
            blocks.append(block_entry(filepath, old_entry, new_entry))

    for filepath, old_entry in old_map.items():
        if filepath not in new_map:
            changed.append(base_name(old_entry["name"]))
            blocks.append(block_entry(filepath, old_entry, None))

    if not blocks:
        print("auto: update INDEX")
        return

    print(f"auto: update INDEX [{', '.join(changed)}]")
    print()
    print("\n\n".join(blocks))
    print()


if __name__ == "__main__":
    main()
