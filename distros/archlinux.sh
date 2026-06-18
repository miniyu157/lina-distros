#!/usr/bin/env bash

# shellcheck shell=bash
# shellcheck disable=SC2155

cmd::options() {
    local versions_json
    versions_json=$(python3 -c '
import urllib.request, re, json, sys

try:
    url = "https://mirrors.kernel.org/archlinux/iso/"
    with urllib.request.urlopen(url, timeout=10) as resp:
        html = resp.read().decode("utf-8")
    versions = re.findall(r"(\d{4}\.\d{2}\.\d{2})/\"", html)
    versions = sorted(set(versions), reverse=True)
    if not versions:
        raise ValueError("no version directories found")
    print(json.dumps(["latest"] + versions))
except Exception as e:
    print(f"Error: failed to fetch ArchLinux version list: {e}", file=sys.stderr)
    sys.exit(1)
')

    cat << EOF
{
  "archs": ["x86_64"],
  "versions": ${versions_json},
  "mirrors": [
    "https://mirrors.kernel.org/archlinux/iso/",
    "https://mirrors.tuna.tsinghua.edu.cn/archlinux/iso/",
    "https://mirrors.aliyun.com/archlinux/iso/",
    "https://mirrors.ustc.edu.cn/archlinux/iso/"
  ]
}
EOF
}

cmd::info() {
    cat << 'EOF'
{
  "name": "archlinux",
  "desc": "ArchLinux"
}
EOF
}

cmd::get() {
    local version="${1:-}" arch="${2:-}" mirror="${3:-}"
    [[ -z $version || -z $arch || -z $mirror ]] && usage

    local hashes_url="${mirror}${version}/sha256sums.txt"
    local fetch_result=$(curl -fsSL --connect-timeout 10 --max-time 30 "$hashes_url" | awk '$2 ~ /^archlinux-bootstrap-[0-9]{4}\.[0-9]{2}\.[0-9]{2}-x86_64\.tar\.zst$/ {print $1, $2}')
    [[ -z $fetch_result ]] && {
        printf "Error: Failed to fetch hash from %s\n" "$hashes_url" >&2
        return 1
    }
    local hash_val filename
    read -r hash_val filename <<< "$fetch_result"
    local src="${mirror}${version}/${filename}"

    cat << EOF
{
  "src": "${src}",
  "ext": {
    "hash_val": "sha256:${hash_val}",
    "find": "."
  }
}
EOF
}

cmd::get::usage() {
    printf "  get <version> <arch> <mirror>\n" >&2
}

# ── Generic template: subcommand dispatch & usage display ──
usage() {
    local cmds=$(compgen -A function cmd:: | sed -n 's/^cmd::\([^:]*\)$/\1/p' | paste -sd '|')
    printf "usage: %s {%s}\n" "$0" "$cmds" >&2
    local fn
    for fn in $(compgen -A function cmd:: | sed -n '/::usage$/p'); do
        "$fn"
    done
    exit 1
}

main() {
    set -euo pipefail
    shopt -s inherit_errexit 2> /dev/null || true
    local fn="cmd::${1:-}"
    if declare -f "$fn" > /dev/null 2>&1; then
        "$fn" "${@:2}"
    else
        usage
    fi
}

[[ ${BASH_SOURCE[0]} == "${0}" ]] && main "$@"
