#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VERSION = "v1"


def validate_path(path: str) -> Path:
    """
    验证目录合法。
    """
    if path in frozenset({".", ".."}):
        print(f"错误: 禁止使用的名称: '{path}'", file=sys.stderr)
        sys.exit(1)
    if "/" in path or "\\" in path:
        print(f"错误: 不允许含路径分隔符: '{path}'", file=sys.stderr)
        sys.exit(1)

    cwd = Path.cwd()
    resolved = (cwd / path).resolve()

    try:
        resolved.relative_to(cwd)
    except ValueError:
        print(f"错误: '{path}' 解析后不在当前目录下", file=sys.stderr)
        sys.exit(1)

    if not resolved.is_dir():
        print(f"错误: 目录不存在: {path}", file=sys.stderr)
        sys.exit(1)

    return resolved


def iter_executables(distros_dir: Path):
    """
    扫描目录里的可执行文件。
    """
    for p in sorted(distros_dir.iterdir()):
        if p.is_file() and not p.name.startswith(".") and os.access(p, os.X_OK):
            yield p


def run_json(script: Path, subcommand: str) -> dict | None:
    """
    传入小程序子命令，获取 JSON。
    """
    try:
        r = subprocess.run([str(script), subcommand], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return None
        data = json.loads(r.stdout)
        if not isinstance(data, dict) or not data:
            return None
        return data
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None


def compute_file_hash(script: Path) -> str:
    """
    获取一个文件的 sha256
    """
    return hashlib.sha256(script.read_bytes()).hexdigest()


def build_entries(dirs: list[Path]) -> list[dict]:
    """
    获取发行版数据文件的 JSON 输出，进行编排。
    """
    entries: list[dict] = []
    for d in dirs:
        for script in iter_executables(d):
            info_data = run_json(script, "info")
            options_data = run_json(script, "options")

            if info_data is None or options_data is None:
                print(f"错误: 无效的发行版脚本: {script}", file=sys.stderr)
                sys.exit(1)

            # 构造 entry
            entry: dict[str, object] = {}
            entry.update(info_data)
            file_hash = compute_file_hash(script)
            entry["name"] = f"{entry['name']}.{file_hash[:7]}"
            entry["exec"] = {
                "file": str(script.relative_to(SCRIPT_DIR)),
                "options": options_data,
            }
            entries.append(entry)
    return entries


def _is_primitive_list(obj: object) -> bool:
    """判断是否为纯量列表（非 dict/list 的元素）。"""
    return isinstance(obj, list) and all(not isinstance(item, (dict, list)) for item in obj)


def _format_json(obj: object, indent: int = 0) -> str:
    """自定义 JSON 格式化: 纯量数组保持单行密集输出。"""
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
            "扫描发行版小程序脚本，进行编排索引。\n"
            f"遵循 {VERSION} 版本规范调用各脚本的 info/options 子命令。\n"
            "始终打印编排后的 JSON 到标准输出。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("dirs", nargs="+", metavar="dir", help="发行版子目录名，至少提供一个（相对于当前目录）")
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args()

    # 验证 dirs 参数
    dirs = [validate_path(n) for n in args.dirs]

    index = {
        "version": VERSION,
        "entries": build_entries(dirs),
    }
    sys.stdout.write(_format_json(index) + "\n")


if __name__ == "__main__":
    main()
