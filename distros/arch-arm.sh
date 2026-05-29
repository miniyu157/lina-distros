#!/usr/bin/env bash

# shellcheck shell=bash

set -euo pipefail
shopt -s inherit_errexit 2> /dev/null || true

info() {
    cat << 'EOF'
{
  "desc": "ArchLinux ARM (os.archlinuxarm.org)",
  "archs": ["aarch64"],
  "versions": ["latest"]
}
EOF
}

get() {
    local version="${1}" arch="${2}"
    [[ -z $version || -z $arch ]] && usage

    local src="http://os.archlinuxarm.org/os/ArchLinuxARM-aarch64-latest.tar.gz"
    local md5_url="http://os.archlinuxarm.org/os/ArchLinuxARM-aarch64-latest.tar.gz.md5"
    local hash_val
    hash_val=$(curl -fsSL --connect-timeout 10 --max-time 30 "$md5_url" | awk '{print $1}')
    [[ -z $hash_val ]] && {
        printf "Error: Failed to fetch hash from %s\n" "$md5_url" >&2
        return 1
    }

    cat << EOF
{
  "src": "${src}",
  "hash_val": "${hash_val}",
  "hash_cmd": "md5sum"
}
EOF
}

usage() {
    echo "usage: $0 {info | get <version> <arch> }" >&2
    exit 1
}

main() {
    case "${1:-}" in
        info)
            info
            ;;
        get)
            get "${2:-}" "${3:-}"
            ;;
        *) usage ;;
    esac
}

[[ ${BASH_SOURCE[0]} == "${0}" ]] && main "$@"
