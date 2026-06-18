#!/usr/bin/env bash

# shellcheck shell=bash
# shellcheck disable=SC2155

cmd::options() {
    cat << 'EOF'
{
  "archs": ["x86_64", "aarch64", "ppc64le", "s390x"],
  "versions": ["8", "9", "10"],
  "mirrors": [
    "https://dl.rockylinux.org/pub/rocky",
    "https://mirrors.ustc.edu.cn/rocky",
    "https://mirrors.aliyun.com/rockylinux"
  ]
}
EOF
}

cmd::info() {
    cat << 'EOF'
{
  "name": "rocky",
  "desc": "Rocky Linux"
}
EOF
}

cmd::get() {
    local version="${1:-}" arch="${2:-}" mirror="${3:-}"
    [[ -z $version || -z $arch || -z $mirror ]] && usage

    local tar_file="Rocky-${version}-Container-Base.latest.${arch}.tar.xz"
    local base_url="${mirror}/${version}/images/${arch}/"
    local checksum_url="${base_url}${tar_file}.CHECKSUM"
    local checksum_text=$(curl -fsSL --connect-timeout 10 --max-time 30 "$checksum_url")
    local hash_val=$(echo "$checksum_text" | awk -F' = ' '/^SHA256.*Container-Base/{print $2}')
    [[ -z $hash_val ]] && {
        printf "Error: Unrecognized remote format: %s\n" "$checksum_url" >&2
        return 1
    }
    local src="${base_url}${tar_file}"

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
