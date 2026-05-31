#!/usr/bin/env bash

# shellcheck shell=bash

set -euo pipefail
shopt -s inherit_errexit 2> /dev/null || true

info() {
    cat << 'EOF'
{
  "desc": "Alpine Linux",
  "archs": ["aarch64", "x86_64"],
  "versions": ["latest-stable"],
  "mirrors": [
    "https://mirrors.tuna.tsinghua.edu.cn/alpine/",
    "https://mirrors.aliyun.com/alpine/",
    "https://mirror.xtom.com.hk/alpine/",
    "https://dl-cdn.alpinelinux.org/alpine/"
  ]
}
EOF
}

get() {
    local default_mirror='https://dl-cdn.alpinelinux.org/alpine/'
    local version="${1}" arch="${2}" mirror="${3:-$default_mirror}"
    [[ -z $version || -z $arch ]] && usage

    local yaml_url="${mirror}${version}/releases/${arch}/latest-releases.yaml"
    local yaml_text
    yaml_text=$(curl -fsSL --connect-timeout 10 --max-time 30 "$yaml_url")
    local filename
    filename=$(echo "$yaml_text" | awk '/flavor: alpine-minirootfs/{found=1} found && /^  file: /{print $2; exit}')
    local hash_val
    hash_val=$(echo "$yaml_text" | awk '/flavor: alpine-minirootfs/{found=1} found && /^  sha256: /{print $2; exit}')
    [[ -z $filename || -z $hash_val ]] && {
        printf "Error: Unrecognized remote format: %s\n" "$yaml_url" >&2
        return 1
    }
    local src
    src="${mirror}${version}/releases/${arch}/${filename}"

    cat << EOF
{
  "src": "${src}",
  "hash_val": "sha256:${hash_val}"
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
