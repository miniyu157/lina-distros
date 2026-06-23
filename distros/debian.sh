#!/usr/bin/env bash

# shellcheck shell=bash
# shellcheck disable=SC2155

cmd::options() {
    cat << 'EOF'
{
  "archs": ["x86_64", "aarch64", "armhf"],
  "versions": ["14", "forky", "13", "trixie", "12", "bookworm", "11", "bullseye"],
  "mirrors": [
    "http://images.linuxcontainers.org"
  ]
}
EOF
}

cmd::info() {
    cat << 'EOF'
{
  "name": "debian",
  "desc": "Debian GNU/Linux"
}
EOF
}

cmd::get() {
    local version="${1:-}" arch="${2:-}" mirror="${3:-}"
    [[ -z $version || -z $arch || -z $mirror ]] && usage

    local lxc_arch
    case "$arch" in
        x86_64) lxc_arch="amd64" ;;
        aarch64) lxc_arch="arm64" ;;
        armhf) lxc_arch="armhf" ;;
        *)
            printf "Error: Unsupported arch: %s\n" "$arch" >&2
            return 1
            ;;
    esac

    local codename
    case "$version" in
        11) codename="bullseye" ;;
        12) codename="bookworm" ;;
        13) codename="trixie" ;;
        14) codename="forky" ;;
        *) codename="$version" ;;
    esac

    local list_url="${mirror}/images/debian/${codename}/${lxc_arch}/default/"
    local listing=$(curl -4fsSL --connect-timeout 10 --max-time 30 "$list_url")
    [[ -z $listing ]] && {
        printf "Error: Failed to fetch directory listing: %s\n" "$list_url" >&2
        return 1
    }

    local date_dir=$(echo "$listing" | awk -F'"' '/href="/{print $2}' | grep -E '^[0-9]{8}_[0-9]{2}%3A[0-9]{2}/$' | sort | tail -1)
    [[ -z $date_dir ]] && {
        printf "Error: No build date directory found for version=%s arch=%s\n" "$version" "$arch" >&2
        return 1
    }

    local base_url="${list_url}${date_dir}"
    local sums_text=$(curl -4fsSL --connect-timeout 10 --max-time 30 "${base_url}SHA256SUMS")
    local hash_val=$(echo "$sums_text" | awk '/rootfs\.tar\.xz/ {print $1}')
    [[ -z $hash_val ]] && {
        printf "Error: Unrecognized SHA256SUMS format: %s\n" "${base_url}SHA256SUMS" >&2
        return 1
    }
    local src="${base_url}rootfs.tar.xz"

    cat << EOF
{
  "src": "${src}",
  "type": "tarball",
  "ext": {
    "hash_val": "sha256:${hash_val}"
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
