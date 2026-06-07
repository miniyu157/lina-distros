#!/usr/bin/env bash

# shellcheck shell=bash

set -euo pipefail
shopt -s inherit_errexit 2> /dev/null || true

options() {
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

info() {
    cat << 'EOF'
{
  "name": "rocky",
  "desc": "Rocky Linux"
}
EOF
}

get() {
    local version="${1}" arch="${2}" mirror="${3}"
    [[ -z $version || -z $arch || -z $mirror ]] && usage

    local tar_file="Rocky-${version}-Container-Base.latest.${arch}.tar.xz"
    local base_url="${mirror}/${version}/images/${arch}/"
    local checksum_url="${base_url}${tar_file}.CHECKSUM"

    local checksum_text
    checksum_text=$(curl -fsSL --connect-timeout 10 --max-time 30 "$checksum_url")
    local hash_val
    hash_val=$(echo "$checksum_text" | awk -F' = ' '/^SHA256.*Container-Base/{print $2}')
    [[ -z $hash_val ]] && {
        printf "Error: Unrecognized remote format: %s\n" "$checksum_url" >&2
        return 1
    }
    local src="${base_url}${tar_file}"

    cat << EOF
{
  "src": "${src}",
  "hash_val": "sha256:${hash_val}"
}
EOF
}

usage() {
    echo "usage: $0 {options | info | get <version> <arch> <mirror> }" >&2
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
