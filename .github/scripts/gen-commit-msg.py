#!/usr/bin/env python3
"""Compare old and new INDEX, print a meaningful commit message to stdout."""
import json
import sys


def main() -> None:
    changes: list[str] = []

    # Read old INDEX (first run → "initial build")
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

    for filepath, entry in new_map.items():
        old_entry = old_map.get(filepath)
        desc = entry["desc"]

        if old_entry is None:
            changes.append(f"{desc}: new")
            continue

        old_ver = set(old_entry["exec"]["options"]["versions"])
        new_ver = set(entry["exec"]["options"]["versions"])
        added = sorted(new_ver - old_ver)
        removed = sorted(old_ver - new_ver)

        parts: list[str] = []
        if added:
            parts.append("+" + ",".join(added))
        if removed:
            parts.append("-" + ",".join(removed))

        if parts:
            changes.append(f"{desc}: {' '.join(parts)}")
        elif entry["name"] != old_entry["name"]:
            # Script hash changed but versions unchanged
            changes.append(f"{desc}: script updated")

    for filepath, old_entry in old_map.items():
        if filepath not in new_map:
            changes.append(f"{old_entry['desc']}: removed")

    if changes:
        body = "; ".join(changes[:3])
        tail = f" [+{len(changes) - 3} more]" if len(changes) > 3 else ""
        print(f"auto: update INDEX ({body}){tail}")
    else:
        print("auto: update INDEX")


if __name__ == "__main__":
    main()
