#!/usr/bin/env bash

# shellcheck shell=bash

set -euo pipefail
shopt -s inherit_errexit 2> /dev/null || true

info() {
    cat << 'EOF'
{
  "desc": "Ubuntu Base (cdimage.ubuntu.com)",
  "archs": ["aarch64", "x86_64"],
  "versions": ["14.04", "16.04", "18.04", "20.04", "22.04", "24.04", "25.10", "26.04"]
}
EOF
}

get() {
    local version="${1}" arch="${2}"
    [[ -z $version || -z $arch ]] && usage

    local arch_pattern
    case "$arch" in
        aarch64) arch_pattern="base-arm64.tar.gz" ;;
        x86_64) arch_pattern="base-amd64.tar.gz" ;;
        *)
            printf "Error: Unsupported arch: %s\n" "$arch" >&2
            return 1
            ;;
    esac

    local sum_url="https://cdimage.ubuntu.com/ubuntu-base/releases/${version}/release/SHA256SUMS"
    local tar_file
    tar_file=$(curl -fsSL --connect-timeout 10 --max-time 30 "$sum_url" | grep "$arch_pattern" | awk '{print $2}' | sed 's/^\*//' | sort -V | tail -1)
    [[ -z $tar_file ]] && {
        printf "Error: No matching tarball found for arch=%s version=%s\n" "$arch" "$version" >&2
        return 1
    }

    local hash_val
    hash_val=$(curl -fsSL --connect-timeout 10 --max-time 30 "$sum_url" | grep "${tar_file}" | awk '{print $1}')
    [[ -z $hash_val ]] && {
        printf "Error: Failed to fetch hash for %s\n" "$tar_file" >&2
        return 1
    }

    local src="https://cdimage.ubuntu.com/ubuntu-base/releases/${version}/release/${tar_file}"

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
