#!/usr/bin/env bash

# shellcheck shell=bash
# shellcheck disable=SC2155

cmd::options() {
    cat << 'EOF'
{
  "archs": ["aarch64", "armhf", "armv7", "loongarch64", "ppc64le", "riscv64", "s390x", "x86", "x86_64"],
  "versions": ["latest-stable"],
  "mirrors": [
    "https://dl-cdn.alpinelinux.org/alpine/",
    "https://mirrors.tuna.tsinghua.edu.cn/alpine/",
    "https://mirrors.aliyun.com/alpine/",
    "https://mirror.xtom.com.hk/alpine/"
  ]
}
EOF
}

cmd::info() {
    cat << 'EOF'
{
  "name": "alpine",
  "desc": "Alpine Linux"
}
EOF
}

cmd::get() {
    local version="${1:-}" arch="${2:-}" mirror="${3:-}"
    [[ -z $version || -z $arch || -z $mirror ]] && usage

    local yaml_url="${mirror}${version}/releases/${arch}/latest-releases.yaml"
    local yaml_text=$(curl -fsSL --connect-timeout 10 --max-time 30 "$yaml_url")
    local filename=$(echo "$yaml_text" | awk '/flavor: alpine-minirootfs/{found=1} found && /^  file: /{print $2; exit}')
    local hash_val=$(echo "$yaml_text" | awk '/flavor: alpine-minirootfs/{found=1} found && /^  sha256: /{print $2; exit}')
    [[ -z $filename || -z $hash_val ]] && {
        printf "Error: Unrecognized remote format: %s\n" "$yaml_url" >&2
        return 1
    }
    local src="${mirror}${version}/releases/${arch}/${filename}"

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
