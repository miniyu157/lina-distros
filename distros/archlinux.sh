#!/usr/bin/env bash

# shellcheck shell=bash

set -euo pipefail
shopt -s inherit_errexit 2> /dev/null || true

info() {
    cat << 'EOF'
{
  "desc": "ArchLinux",
  "archs": ["x86_64"],
  "versions": ["latest", "2026.05.01", "2026.04.01", "2026.03.01"],
  "mirrors": [
    "https://mirrors.tuna.tsinghua.edu.cn/archlinux/iso/",
    "https://mirrors.aliyun.com/archlinux/iso/",
    "https://mirrors.ustc.edu.cn/archlinux/iso/"
  ]
}
EOF
}

get() {
    local default_mirror='https://mirrors.tuna.tsinghua.edu.cn/archlinux/iso/'
    local version="${1}" arch="${2}" mirror="${3:-$default_mirror}"
    [[ -z $version || -z $arch ]] && usage

    [[ $arch != "x86_64" ]] && {
        printf "Error: Arch Linux only supports x86_64 architecture.\n" >&2
        return 1
    }

    local hashes_url="${mirror}${version}/sha256sums.txt"
    local hash_val filename

    local fetch_result
    fetch_result=$(curl -fsSL --connect-timeout 10 --max-time 30 "$hashes_url" | awk '$2 ~ /^archlinux-bootstrap-[0-9]{4}\.[0-9]{2}\.[0-9]{2}-x86_64\.tar\.zst$/ {print $1, $2}')
    [[ -z $fetch_result ]] && {
        printf "Error: Failed to fetch hash from %s\n" "$hashes_url" >&2
        return 1
    }

    read -r hash_val filename <<< "$fetch_result"

    local src="${mirror}${version}/${filename}"

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
