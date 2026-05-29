#!/usr/bin/env bash

# shellcheck shell=bash

set -euo pipefail
shopt -s inherit_errexit 2> /dev/null || true

info() {
    cat << 'EOF'
{
  "desc": "ArchLinux (mirrors.tuna.tsinghua.edu.cn)",
  "archs": ["x86_64"],
  "versions": ["latest"]
}
EOF
}

get() {
    local version="${1}" arch="${2}"
    [[ -z $version || -z $arch ]] && usage

    local target_file="archlinux-bootstrap-x86_64.tar.zst"
    local hash_url="https://mirrors.tuna.tsinghua.edu.cn/archlinux/iso/latest/sha256sums.txt"
    local src="https://mirrors.tuna.tsinghua.edu.cn/archlinux/iso/latest/${target_file}"

    local hash_val
    hash_val=$(curl -fsSL --connect-timeout 10 --max-time 30 "$hash_url" | grep "$target_file" | awk '{print $1}')
    [[ -z $hash_val ]] && {
        printf "Error: Failed to fetch hash from %s\n" "$hash_url" >&2
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
