#!/usr/bin/env bash

# shellcheck shell=bash

set -euo pipefail
shopt -s inherit_errexit 2> /dev/null || true

options() {
    cat << 'EOF'
{
  "archs": ["x86_64", "aarch64", "armhf"],
  "versions": ["bookworm", "bullseye", "trixie", "forky"],
  "mirrors": [
    "http://images.linuxcontainers.org"
  ]
}
EOF
}

info() {
    cat << 'EOF'
{
  "name": "debian",
  "desc": "Debian GNU/Linux"
}
EOF
}

get() {
    local version="${1}" arch="${2}" mirror="${3}"
    [[ -z $version || -z $arch || -z $mirror ]] && usage

    local lxc_arch
    case "$arch" in
        x86_64)  lxc_arch="amd64" ;;
        aarch64) lxc_arch="arm64" ;;
        armhf)   lxc_arch="armhf" ;;
        *)
            printf "Error: Unsupported arch: %s\n" "$arch" >&2
            return 1
            ;;
    esac

    local list_url="${mirror}/images/debian/${version}/${lxc_arch}/default/"
    local listing
    listing=$(curl -4fsSL --connect-timeout 10 --max-time 30 "$list_url")
    [[ -z $listing ]] && {
        printf "Error: Failed to fetch directory listing: %s\n" "$list_url" >&2
        return 1
    }

    local date_dir
    date_dir=$(echo "$listing" | awk -F'"' '/href="/{print $2}' | grep -E '^[0-9]{8}_[0-9]{2}%3A[0-9]{2}/$' | sort | tail -1)
    [[ -z $date_dir ]] && {
        printf "Error: No build date directory found for version=%s arch=%s\n" "$version" "$arch" >&2
        return 1
    }

    local base_url="${list_url}${date_dir}"
    local sums_text
    sums_text=$(curl -4fsSL --connect-timeout 10 --max-time 30 "${base_url}SHA256SUMS")
    local hash_val
    hash_val=$(echo "$sums_text" | awk '/rootfs\.tar\.xz/ {print $1}')
    [[ -z $hash_val ]] && {
        printf "Error: Unrecognized SHA256SUMS format: %s\n" "${base_url}SHA256SUMS" >&2
        return 1
    }
    local src="${base_url}rootfs.tar.xz"

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
