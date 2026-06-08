#!/usr/bin/env bash

# shellcheck shell=bash

set -euo pipefail
shopt -s inherit_errexit 2> /dev/null || true

options() {
    local versions_json
    versions_json=$(python3 -c '
import urllib.request, re, json, sys

try:
    url = "https://mirrors.ustc.edu.cn/fedora/releases/"
    with urllib.request.urlopen(url, timeout=15) as resp:
        html = resp.read().decode("utf-8")
    versions = re.findall(r"href=\"[^\"]*/(\d+)/\"", html)
    versions = sorted({int(v) for v in versions if 30 <= int(v) <= 99}, reverse=True)
    versions = [str(v) for v in versions]
    if not versions:
        raise ValueError("no version directories found")
    print(json.dumps(versions))
except Exception as e:
    print(f"Error: failed to fetch Fedora version list: {e}", file=sys.stderr)
    sys.exit(1)
')

    cat << EOF
{
  "archs": ["x86_64", "aarch64"],
  "versions": ${versions_json},
  "mirrors": [
    "https://dl.fedoraproject.org/pub/fedora",
    "https://mirrors.tuna.tsinghua.edu.cn/fedora",
    "https://mirrors.ustc.edu.cn/fedora",
    "https://mirrors.aliyun.com/fedora"
  ]
}
EOF
}

info() {
    cat << 'EOF'
{
  "name": "fedora",
  "desc": "Fedora Linux"
}
EOF
}

get() {
    local version="${1}" arch="${2}" mirror="${3}"
    [[ -z $version || -z $arch || -z $mirror ]] && usage

    local list_url="${mirror}/releases/${version}/Container/${arch}/images/"
    local listing
    listing=$(curl -fsSL --connect-timeout 10 --max-time 30 "$list_url")
    [[ -z $listing ]] && {
        printf "Error: Failed to fetch directory listing: %s\n" "$list_url" >&2
        return 1
    }

    local checksum_file
    checksum_file=$(echo "$listing" | grep -o 'href="[^"]*"' | sed 's/^href="//;s/"$//' | grep "${arch}-CHECKSUM" | sed 's|.*/||' | head -1)
    [[ -z $checksum_file ]] && {
        printf "Error: No CHECKSUM file found for version=%s arch=%s\n" "$version" "$arch" >&2
        return 1
    }

    local checksum_text
    checksum_text=$(curl -fsSL --connect-timeout 10 --max-time 30 "${list_url}${checksum_file}")
    [[ -z $checksum_text ]] && {
        printf "Error: Failed to fetch CHECKSUM: %s\n" "${list_url}${checksum_file}" >&2
        return 1
    }

    local tar_file hash_val
    tar_file=$(echo "$checksum_text" | awk -F'[()]' '/^SHA256.*Container-Base-Generic-[0-9]/{print $2; exit}')
    hash_val=$(echo "$checksum_text" | awk -F' = ' '/^SHA256.*Container-Base-Generic-[0-9]/{print $2; exit}')
    [[ -z $tar_file || -z $hash_val ]] && {
        printf "Error: Unrecognized CHECKSUM format: %s\n" "${list_url}${checksum_file}" >&2
        return 1
    }

    local src="${list_url}${tar_file}"

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
