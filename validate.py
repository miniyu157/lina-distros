#!/usr/bin/env python3
"""Validate SRC URLs and HASH_VAL for distro definitions."""

import argparse
import json
import math
import signal
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import NamedTuple

# === Constants ===

EXPECTED_VERSION = "v3.3"
DISTROS_DIR = "distros"
SCRIPT_DIR = Path(__file__).resolve().parent
BUILD_INDEX = SCRIPT_DIR / "build_INDEX.py"

KNOWN_HASHES = {
    "md5": 32,
    "sha1": 40,
    "sha256": 64,
    "sha384": 96,
    "sha512": 128,
    "sha3-256": 64,
    "sha3-384": 96,
    "sha3-512": 128,
    "b2": 128,
    "blake2b": 128,
    "blake2s": 64,
}


class Color:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


# === Types ===


class DistroRow(NamedTuple):
    name: str
    desc: str
    file: str
    archs: list[str]
    versions: list[str]


class HashResult(NamedTuple):
    status: str
    display: str


class CellResult(NamedTuple):
    file: str
    arch: str
    version: str
    src: str
    src_status: int
    src_size: int
    src_error: str
    hash_status: str
    hash_display: str


# === Utilities ===


def resolve_build_index(path: Path | None) -> Path:
    resolved = path or BUILD_INDEX
    if not resolved.is_file():
        print(f"错误: build_INDEX 脚本未找到: {resolved}", file=sys.stderr)
        sys.exit(1)
    return resolved


def try_semantic_sort(versions: list[str]) -> list[str]:
    try:
        parsed = [tuple(int(x) for x in v.split(".")) for v in versions]
        return [v for _, v in sorted(zip(parsed, versions))]
    except (ValueError, TypeError):
        return list(versions)


def sample_items(items: list[str], limit: int) -> list[str]:
    if limit <= 0 or not items:
        return []
    if len(items) <= limit:
        return list(items)
    oldest_n = math.ceil(limit / 2)
    newest_n = math.floor(limit / 2)
    sampled = items[:oldest_n] + (items[-newest_n:] if newest_n else [])
    return list(dict.fromkeys(sampled))


def truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    if max_len <= 3:
        return s[:max_len]
    return s[: max_len - 3] + "..."


def format_size(n: int) -> str:
    if n <= 0:
        return "-"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def resolve_path(query: str, candidates: list[str]) -> str | None:
    if query in candidates:
        return query

    if query.startswith("./"):
        alt = query[2:]
    else:
        alt = "./" + query
    if alt in candidates:
        return alt

    try:
        qp = Path(query)
        if qp.is_absolute():
            try:
                rel = str(qp.resolve().relative_to(SCRIPT_DIR.resolve()))
            except ValueError:
                return None
            if rel in candidates:
                return rel
            if "./" + rel in candidates:
                return "./" + rel
        else:
            try:
                abs_path = (SCRIPT_DIR / qp).resolve()
                rel = str(abs_path.relative_to(SCRIPT_DIR.resolve()))
            except (ValueError, OSError):
                return None
            if rel in candidates:
                return rel
            if "./" + rel in candidates:
                return "./" + rel
    except (ValueError, OSError):
        pass

    return None


# === Core Validation ===


def check_version(build_index: Path) -> tuple[bool, str]:
    try:
        r = subprocess.run(
            [sys.executable, str(build_index), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        actual = r.stdout.strip()
        return actual == EXPECTED_VERSION, actual
    except (subprocess.TimeoutExpired, OSError) as e:
        return False, str(e)


def parse_index(build_index: Path) -> list[DistroRow]:
    try:
        r = subprocess.run(
            [sys.executable, str(build_index), DISTROS_DIR],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"{Color.RED}build_INDEX.py failed: {e}{Color.RESET}")
        sys.exit(1)

    if r.returncode != 0:
        print(f"{Color.RED}build_INDEX.py failed (rc={r.returncode}):{Color.RESET}")
        print(r.stderr)
        sys.exit(1)

    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        print(f"{Color.RED}build_INDEX.py output is not valid JSON: {e}{Color.RESET}")
        sys.exit(1)

    if data.get("version") != EXPECTED_VERSION:
        print(
            f"{Color.RED}INDEX version mismatch: expected '{EXPECTED_VERSION}', "
            f"got '{data.get('version', '')}'{Color.RESET}"
        )
        sys.exit(1)

    rows = []
    for entry in data.get("entries", []):
        exec_data = entry.get("exec", {})
        exec_options = exec_data.get("options", {})
        rows.append(
            DistroRow(
                name=entry.get("name", ""),
                desc=entry.get("desc", ""),
                file=exec_data.get("file", ""),
                archs=exec_options.get("archs", []),
                versions=exec_options.get("versions", []),
            )
        )
    return rows



def resolve_distro_get(filepath: Path, version: str, arch: str) -> dict[str, str]:
    try:
        r = subprocess.run(
            ["bash", str(filepath), "get", version, arch],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if r.returncode != 0:
            return {}
        return json.loads(r.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return {}


def head_request(url: str, timeout: int = 15) -> tuple[int, int, str]:
    if not url:
        return 0, 0, "empty SRC"
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            cl = resp.headers.get("Content-Length", "0")
            size = int(cl) if cl.isdigit() else 0
            return resp.status, size, ""
    except urllib.error.HTTPError as e:
        cl = e.headers.get("Content-Length", "0") if e.headers else "0"
        size = int(cl) if cl and cl.isdigit() else 0
        return e.code, size, f"HTTP {e.code}"
    except (urllib.error.URLError, OSError, ValueError) as e:
        return 0, 0, str(e)


def check_hash_val(hash_val: str) -> HashResult:
    if not hash_val:
        return HashResult("FAIL", "FAIL")
    if hash_val == "SKIP":
        return HashResult("SKIP", "SKIP")
    if ":" not in hash_val:
        return HashResult("FAIL", "FAIL")

    algo, hex_val = hash_val.split(":", 1)

    if not algo or not hex_val:
        return HashResult("FAIL", "FAIL")

    hex_chars = set("0123456789abcdefABCDEF")
    if not all(c in hex_chars for c in hex_val):
        return HashResult("FAIL", "FAIL")

    algo = algo.lower()
    expected_len = KNOWN_HASHES.get(algo)
    if expected_len is None:
        return HashResult("PASS", f"{algo}(?)")
    if len(hex_val) != expected_len:
        return HashResult("FAIL", f"{algo}(len!)")
    return HashResult("PASS", algo)


# === Report ===


def build_report_table(results: list[CellResult]) -> str:
    if not results:
        return f"{Color.YELLOW}No cells to display.{Color.RESET}"

    rows = []
    max_w = {"file": 5, "arch": 4, "version": 7, "src": 3, "hash": 5}

    for r in results:
        if r.src:
            filename = urllib.parse.urlparse(r.src).path.rstrip("/").rsplit("/", 1)[-1] or "-"
        else:
            filename = "-"
        if r.src_status and not r.src_error:
            src_display = f"{r.src_status} {format_size(r.src_size)} {filename}"
        else:
            src_display = f"{r.src_status or 'ERR'} {r.src_error or '-'}"

        hash_display = r.hash_display

        rows.append(
            {
                "file": r.file,
                "arch": r.arch,
                "version": r.version,
                "src": src_display,
                "hash": hash_display,
            }
        )
        for k in max_w:
            max_w[k] = max(max_w[k], len(rows[-1][k]))

    caps = {"file": 35, "src": 60, "hash": 40}
    for k, cap in caps.items():
        max_w[k] = min(max_w[k], cap)

    def cell(text: str, width: int) -> str:
        return truncate(text, width).ljust(width)

    header = (
        f"{Color.BOLD}{Color.CYAN}"
        f"{cell('File', max_w['file'])}  "
        f"{cell('Arch', max_w['arch'])}  "
        f"{cell('Version', max_w['version'])}  "
        f"{cell('SRC', max_w['src'])}  "
        f"{cell('Hash', max_w['hash'])}"
        f"{Color.RESET}"
    )

    lines = [header]
    for r, row in zip(results, rows):
        src_color = Color.GREEN if r.src_status == 200 and not r.src_error else Color.RED

        h = r.hash_status
        if h == "FAIL":
            hash_color = Color.RED
        elif h == "SKIP":
            hash_color = Color.DIM
        else:
            hash_color = Color.GREEN

        line = (
            f"{cell(row['file'], max_w['file'])}  "
            f"{cell(row['arch'], max_w['arch'])}  "
            f"{cell(row['version'], max_w['version'])}  "
            f"{src_color}{cell(row['src'], max_w['src'])}{Color.RESET}  "
            f"{hash_color}{cell(row['hash'], max_w['hash'])}{Color.RESET}"
        )
        lines.append(line)

    return "\n".join(lines)


def print_summary(results: list[CellResult]) -> None:
    total = len(results)
    passed = sum(1 for r in results if r.src_status == 200 and not r.src_error and r.hash_status in ("PASS", "SKIP"))
    failed = total - passed
    skipped = sum(1 for r in results if r.hash_status == "SKIP")

    if failed:
        tag = f"{Color.RED}FAIL{Color.RESET}"
    else:
        tag = f"{Color.GREEN}PASS{Color.RESET}"

    parts = [
        f"{Color.BOLD}{tag}{Color.RESET}",
        f"  Total: {total}",
        f"Passed: {passed}",
        f"Failed: {failed}",
    ]
    if skipped:
        parts.append(f"Skipped: {skipped}")
    print("  ".join(parts))


# === CLI ===


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate.py",
        description=f"验证发行版定义的 SRC、HASH_VAL 有效性\n版本: {EXPECTED_VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  %(prog)s\n  %(prog)s --path distros/ubuntu.sh\n  %(prog)s --arch-limit 3 --version-limit 2",
    )
    parser.add_argument(
        "--arch-limit",
        type=int,
        default=5,
        metavar="N",
        help="每个发行版的架构抽样上限（默认: 5）",
    )
    parser.add_argument(
        "--version-limit",
        type=int,
        default=4,
        metavar="N",
        help="每个发行版的版本抽样上限，取最新与最老各一半（默认: 4）",
    )
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        metavar="PATH",
        help="按文件路径筛选发行版定义（如 distros/alpine.sh），支持 ./ 与绝对路径自动解析",
    )
    parser.add_argument(
        "--build-index",
        type=Path,
        default=None,
        metavar="PATH",
        help="指定自定义 INDEX 生成脚本路径（默认: build_INDEX.py）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {EXPECTED_VERSION}",
    )
    return parser


def _sigint_handler(_sig: int, _frame: object) -> None:
    sys.exit(1)


def main() -> None:
    signal.signal(signal.SIGINT, _sigint_handler)

    args = build_argparser().parse_args()

    build_index = resolve_build_index(args.build_index)

    ok, actual = check_version(build_index)
    if not ok:
        print(
            f"错误: 版本不匹配，期望 '{EXPECTED_VERSION}'，实际 '{actual}'",
            file=sys.stderr,
        )
        sys.exit(1)

    distro_rows = parse_index(build_index)

    if args.path:
        matched = resolve_path(args.path, [r.file for r in distro_rows])
        if matched is None:
            print(f"匹配失败: {args.path}", file=sys.stderr)
            sys.exit(1)
        distro_rows = [r for r in distro_rows if r.file == matched]

    results: list[CellResult] = []
    total_distros = len(distro_rows)

    for idx, row in enumerate(distro_rows, 1):
        archs = sample_items(row.archs, args.arch_limit)
        sorted_ver = try_semantic_sort(row.versions)
        versions = sample_items(sorted_ver, args.version_limit)

        if not archs or not versions:
            print(
                f"{Color.YELLOW}[{idx}/{total_distros}] 跳过 {row.file}: "
                f"archs={len(archs)} versions={len(versions)}{Color.RESET}"
            )
            continue

        desc_short = truncate(row.desc, 60)
        print(
            f"{Color.BOLD}{Color.CYAN}[{idx}/{total_distros}]{Color.RESET}"
            f"{Color.BOLD} {row.file}{Color.RESET}  "
            f"{Color.DIM}{desc_short}{Color.RESET}"
        )

        filepath = SCRIPT_DIR / row.file
        for arch in archs:
            for ver in versions:
                d = resolve_distro_get(filepath, ver, arch)
                src_status, src_size, src_error = head_request(d.get("src", ""))
                hash_result = check_hash_val(d.get("hash_val", ""))
                results.append(
                    CellResult(
                        file=row.file,
                        arch=arch,
                        version=ver,
                        src=d.get("src", ""),
                        src_status=src_status,
                        src_size=src_size,
                        src_error=src_error,
                        hash_status=hash_result.status,
                        hash_display=hash_result.display,
                    )
                )

    print()
    print(build_report_table(results))
    print()
    print_summary(results)

    failed = sum(1 for r in results if r.src_status != 200 or r.src_error or r.hash_status == "FAIL")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
