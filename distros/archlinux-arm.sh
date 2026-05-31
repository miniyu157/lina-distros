#!/usr/bin/env bash

# shellcheck shell=bash

set -euo pipefail
shopt -s inherit_errexit 2> /dev/null || true

options() {
    cat << 'EOF'
{
  "archs": ["aarch64"],
  "versions": ["latest"],
  "mirrors": [
    "http://os.archlinuxarm.org/os/"
  ]
}
EOF
}

info() {
    cat << 'EOF'
{
  "name": "archlinux-arm",
  "desc": "ArchLinux ARM"
}
EOF
}

get() {
    local default_mirror='http://os.archlinuxarm.org/os/'
    local version="${1}" arch="${2}" mirror="${3:-$default_mirror}"
    [[ -z $version || -z $arch ]] && usage

    local src="${mirror}ArchLinuxARM-aarch64-latest.tar.gz"
    local md5_url="${mirror}ArchLinuxARM-aarch64-latest.tar.gz.md5"
    local hash_val
    hash_val=$(curl -fsSL --connect-timeout 10 --max-time 30 "$md5_url" | awk '{print $1}')
    [[ -z $hash_val ]] && {
        printf "Error: Failed to fetch hash from %s\n" "$md5_url" >&2
        return 1
    }

    cat << EOF
{
  "src": "${src}",
  "hash_val": "md5:${hash_val}"
}
EOF
}

usage() {
    echo "usage: $0 {options | info | get <version> <arch> [mirror] }" >&2
    exit 1
}

main() {
    case "${1:-}" in
        options)
            options
            ;;
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
