#!/usr/bin/env bash

# shellcheck shell=bash
# shellcheck disable=SC2155

cmd::options() {
    cat << 'EOF'
{
  "archs": ["aarch64"],
  "versions": ["nano", "minimal", "full"],
  "mirrors": [
    "https://kali.download/"
  ]
}
EOF
}

cmd::info() {
    cat << 'EOF'
{
  "name": "kali-nethunter",
  "desc": "Kali NetHunter"
}
EOF
}

cmd::get() {
    local version="${1:-}" arch="${2:-}" mirror="${3:-}"
    [[ -z $version || -z $arch || -z $mirror ]] && usage

    local tar_file="kali-nethunter-rootfs-${version}-arm64.tar.xz"
    local sum_url="${mirror}nethunter-images/current/rootfs/SHA256SUMS"
    local src="${mirror}nethunter-images/current/rootfs/${tar_file}"

    local hash_val=$(curl -fsSL --connect-timeout 10 --max-time 30 "$sum_url" | grep "${tar_file/-rootfs/-.*rootfs}" | awk '{print $1}')
    [[ -z $hash_val ]] && {
        printf "Error: Failed to fetch hash from %s\n" "$sum_url" >&2
        return 1
    }

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
