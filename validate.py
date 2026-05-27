#!/usr/bin/env python3
"""Validate SRC URLs, HASH_VAL, and HASH_CMD for distro definitions."""

import argparse
import math
import re
import signal
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import NamedTuple

# === Constants ===

EXPECTED_VERSION = "# LINA_DISTRO_INDEX v1"
SCRIPT_DIR = Path(__file__).resolve().parent
BUILD_INDEX = SCRIPT_DIR / "build_INDEX.sh"


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
    file: str
    archs: list[str]
    versions: list[str]
    desc: str


class CellResult(NamedTuple):
    file: str
    arch: str
    version: str
    src: str
    src_status: int
    src_size: int
    src_error: str
    hash_val: str
    hash_status: str
    hash_cmd: str


# === Utilities ===


def run_bash(bash_script: str, timeout: int = 60) -> tuple[str, str, int]:
    try:
        r = subprocess.run(
            ["bash", "-c", bash_script],
            capture_output=True, text=True, timeout=timeout,
        )
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", f"timeout after {timeout}s", -1


def resolve_build_index(path: Path | None) -> Path:
    """Resolve the build_INDEX script path; exit if not found."""
    resolved = path or BUILD_INDEX
    if not resolved.is_file():
        print(f"错误: build_INDEX 脚本未找到: {resolved}", file=sys.stderr)
        sys.exit(1)
    return resolved


def try_semantic_sort(versions: list[str]) -> list[str]:
    """Sort versions as dotted-number tuples; keep original order if any fails."""
    try:
        parsed = [tuple(int(x) for x in v.split(".")) for v in versions]
        return [v for _, v in sorted(zip(parsed, versions))]
    except (ValueError, TypeError):
        return list(versions)


def sample_items(items: list[str], limit: int) -> list[str]:
    """Sample oldest ceil(N/2) + newest floor(N/2), deduplicated."""
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
    return s[:max_len - 3] + "..."


def format_size(n: int) -> str:
    if n <= 0:
        return "-"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def resolve_path(query: str, candidates: list[str]) -> str | None:
    """Resolve a user-supplied path against known distro file paths.

    Tries: exact match, strip/add './' prefix, absolute<->relative conversion.
    Returns the matched candidate path or None.
    """
    # 1. Exact match
    if query in candidates:
        return query

    # 2. Strip or add './' prefix
    if query.startswith("./"):
        alt = query[2:]
    else:
        alt = "./" + query
    if alt in candidates:
        return alt

    # 3. Absolute <-> relative (relative to SCRIPT_DIR)
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
    """Verify build_INDEX.sh --version matches expected identifier."""
    stdout, _stderr, _rc = run_bash(f"{build_index} --version")
    actual = stdout.strip()
    return actual == EXPECTED_VERSION, actual


def parse_index(build_index: Path) -> list[DistroRow]:
    """Run build_INDEX.sh and parse its CSV output into DistroRow list."""
    stdout, stderr, rc = run_bash(str(build_index))
    if rc != 0:
        print(f"{Color.RED}build_INDEX.sh failed (rc={rc}):{Color.RESET}")
        print(stderr)
        sys.exit(1)

    rows = []
    for line in stdout.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r'^([^,]+),([^,]+),(.+?)\s{2}#\s(.+)$', line)
        if not m:
            continue
        path, archs_str, versions_str, desc = m.groups()
        archs = archs_str.split()
        versions = versions_str.split()
        rows.append(DistroRow(file=path, archs=archs, versions=versions, desc=desc))
    return rows


def resolve_distro_init(filepath: Path, arch: str, version: str) -> dict[str, str]:
    """Call distro_init with arch-first order; fall back to version-first on failure."""
    for arg1, arg2 in ((arch, version), (version, arch)):
        script = (
            f'source "{filepath}" 2>/dev/null\n'
            f'distro_init "{arg1}" "{arg2}" 2>/dev/null\n'
            f'echo "RC=$?"\n'
            f'printf "SRC=%s\\n" "${{SRC:-}}"\n'
            f'printf "HASH_VAL=%s\\n" "${{HASH_VAL:-}}"\n'
            f'printf "HASH_CMD=%s\\n" "${{HASH_CMD:-}}"\n'
        )
        stdout, _stderr, _rc = run_bash(script)
        result = {}
        for line in stdout.strip().splitlines():
            if not line:
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                result[k] = v
        if result.get("RC") == "0":
            return {
                "SRC": result.get("SRC", ""),
                "HASH_VAL": result.get("HASH_VAL", ""),
                "HASH_CMD": result.get("HASH_CMD", ""),
            }
    return {"SRC": "", "HASH_VAL": "", "HASH_CMD": ""}


def head_request(url: str, timeout: int = 15) -> tuple[int, int, str]:
    """Perform HEAD request. Returns (status_code, content_length, error_string)."""
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


def _hash_algo_tag(hash_val: str) -> str:
    """Return an algorithm tag inferred from hex string length, e.g. '[SHA256]'."""
    if not all(c in "0123456789abcdefABCDEF" for c in hash_val):
        return f"[RAW:{len(hash_val)}]"
    algo_map = {32: "MD5", 40: "SHA1", 64: "SHA256", 128: "SHA512"}
    return f"[{algo_map.get(len(hash_val), f'HEX:{len(hash_val)}')}]"


def check_hash_val(hash_val: str) -> tuple[str, str]:
    """Inspect HASH_VAL.

    Statuses: FAIL (empty), SKIP (literal), URL (reachable hash URL),
              WARN (unreachable URL), PRESENT (raw hash string, unverified).
    """
    if not hash_val:
        return "FAIL", "(empty)"
    if hash_val == "SKIP":
        return "SKIP", "SKIP"
    if hash_val.startswith(("http://", "https://")):
        status, _size, err = head_request(hash_val)
        filename = urllib.parse.urlparse(hash_val).path.rstrip("/").rsplit("/", 1)[-1] or "-"
        if err:
            return "WARN", f"HTTP {status} {filename}" if status else f"{err} {filename}"
        return "URL", f"HTTP {status} {filename}"
    return "PRESENT", _hash_algo_tag(hash_val)


# === Report ===


def _merge_hash_columns(hash_val: str, hash_status: str, hash_cmd: str) -> str:
    """Merge HASH_VAL display and HASH_CMD into a single hash column string."""
    if hash_status == "SKIP":
        return "SKIP"
    if hash_status == "FAIL":
        return hash_val  # "(empty)"

    algo = hash_cmd.replace("sum", "") if hash_cmd else "?"

    if hash_status in ("URL", "WARN"):
        tokens = hash_val.split(" ")
        status_part = " ".join(tokens[:2]) if len(tokens) >= 2 else hash_val
        return f"{algo} [{status_part}]"
    else:  # PRESENT
        return algo


def build_report_table(results: list[CellResult]) -> str:
    if not results:
        return f"{Color.YELLOW}No cells to display.{Color.RESET}"

    rows = []
    max_w = {"file": 5, "arch": 4, "version": 7, "src": 3, "hash": 5}

    for r in results:
        # SRC column: status + size + filename from URL
        if r.src:
            filename = urllib.parse.urlparse(r.src).path.rstrip("/").rsplit("/", 1)[-1] or "-"
        else:
            filename = "-"
        if r.src_status and not r.src_error:
            src_display = f"{r.src_status} {format_size(r.src_size)} {filename}"
        else:
            src_display = f"{r.src_status or 'ERR'} {r.src_error or '-'}"

        hash_display = _merge_hash_columns(r.hash_val, r.hash_status, r.hash_cmd)

        rows.append({
            "file": r.file,
            "arch": r.arch,
            "version": r.version,
            "src": src_display,
            "hash": hash_display,
        })
        for k in max_w:
            max_w[k] = max(max_w[k], len(rows[-1][k]))

    # cap column widths
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
        elif h == "WARN":
            hash_color = Color.YELLOW
        elif h == "SKIP":
            hash_color = Color.DIM
        else:  # "URL" or "PRESENT"
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
    passed = sum(
        1 for r in results
        if r.src_status == 200 and not r.src_error and r.hash_status in ("URL", "PRESENT", "SKIP")
    )
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
        description=f"验证发行版定义的 SRC、HASH_VAL、HASH_CMD 有效性\n版本: {EXPECTED_VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  %(prog)s\n  %(prog)s --path distros/ubuntu.sh\n  %(prog)s --arch-limit 3 --version-limit 2",
    )
    parser.add_argument(
        "--arch-limit", type=int, default=5, metavar="N",
        help="每个发行版的架构抽样上限（默认: 5）",
    )
    parser.add_argument(
        "--version-limit", type=int, default=4, metavar="N",
        help="每个发行版的版本抽样上限，取最新与最老各一半（默认: 4）",
    )
    parser.add_argument(
        "--path", type=str, default=None, metavar="PATH",
        help="按文件路径筛选发行版定义（如 distros/alpine.sh），支持 ./ 与绝对路径自动解析",
    )
    parser.add_argument(
        "--build-index", type=Path, default=None, metavar="PATH",
        help="指定自定义 INDEX 生成脚本路径（默认: build_INDEX.sh）",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {EXPECTED_VERSION}",
    )
    return parser


def _sigint_handler(_sig: int, _frame: object) -> None:
    sys.exit(1)


def main() -> None:
    signal.signal(signal.SIGINT, _sigint_handler)

    args = build_argparser().parse_args()

    # Resolve build index script
    build_index = resolve_build_index(args.build_index)

    # Version check -- silent on success, fail fast on mismatch
    ok, actual = check_version(build_index)
    if not ok:
        print(
            f"错误: 版本不匹配，期望 '{EXPECTED_VERSION}'，实际 '{actual}'",
            file=sys.stderr,
        )
        sys.exit(1)

    # Parse data source
    distro_rows = parse_index(build_index)

    # Filter by --path
    if args.path:
        matched = resolve_path(args.path, [r.file for r in distro_rows])
        if matched is None:
            print(f"匹配失败: {args.path}", file=sys.stderr)
            sys.exit(1)
        distro_rows = [r for r in distro_rows if r.file == matched]

    # Validate
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
                d = resolve_distro_init(filepath, arch, ver)
                src_status, src_size, src_error = head_request(d["SRC"])
                hash_status, hash_display = check_hash_val(d["HASH_VAL"])
                results.append(CellResult(
                    file=row.file,
                    arch=arch,
                    version=ver,
                    src=d["SRC"],
                    src_status=src_status,
                    src_size=src_size,
                    src_error=src_error,
                    hash_val=hash_display,
                    hash_status=hash_status,
                    hash_cmd=d["HASH_CMD"],
                ))

    # Report
    print()
    print(build_report_table(results))
    print()
    print_summary(results)

    failed = sum(1 for r in results if r.src_status != 200 or r.src_error or r.hash_status == "FAIL")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
