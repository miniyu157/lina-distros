#!/usr/bin/env bash

# shellcheck shell=bash

set -euo pipefail
shopt -s inherit_errexit 2> /dev/null || true

info() {
    cat << 'EOF'
{
  "desc": "Kali NetHunter",
  "archs": ["aarch64"],
  "versions": ["nano", "minimal", "full"],
  "mirrors": [
    "https://kali.download/"
  ]
}
EOF
}

get() {
    local default_mirror='https://kali.download/'
    local version="${1}" arch="${2}" mirror="${3:-$default_mirror}"
    [[ -z $version || -z $arch ]] && usage

    local tar_file="kali-nethunter-rootfs-${version}-arm64.tar.xz"
    local sum_url="${mirror}nethunter-images/current/rootfs/SHA256SUMS"
    local src="${mirror}nethunter-images/current/rootfs/${tar_file}"

    local hash_val
    hash_val=$(curl -fsSL --connect-timeout 10 --max-time 30 "$sum_url" | grep "${tar_file/-rootfs/-.*rootfs}" | awk '{print $1}')
    [[ -z $hash_val ]] && {
        printf "Error: Failed to fetch hash from %s\n" "$sum_url" >&2
        return 1
    }

    cat << EOF
{
  "src": "${src}",
  "hash_val": "${hash_val}",
  "hash_cmd": "sha256sum"
}
EOF
}

usage() {
    echo "usage: $0 {info | get <version> <arch> [mirror] }" >&2
    exit 1
}

main() {
    case "${1:-}" in
        info)
            info
            ;;
        get)
            get "${2:-}" "${3:-}" "${4:-}"
            ;;
        *) usage ;;
    esac
}

[[ ${BASH_SOURCE[0]} == "${0}" ]] && main "$@"
