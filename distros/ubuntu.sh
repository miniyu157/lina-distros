#!/usr/bin/env bash

# shellcheck shell=bash
# shellcheck disable=SC2155

cmd::options() {
    local versions_json
    versions_json=$(
        python3 << 'PYEOF'
import urllib.request, re, json, sys

try:
    releases_url = "https://cdimage.ubuntu.com/ubuntu-base/releases/"
    with urllib.request.urlopen(releases_url, timeout=15) as resp:
        html = resp.read().decode("utf-8")

    # Extract XX.XX versions only (point releases like 14.04.1 are excluded)
    versions = sorted(set(re.findall(r"(\d{2}\.\d{2})/\"", html)), reverse=True)
    if not versions:
        raise ValueError("no XX.XX version directories found")

    # Iterate newest->oldest; once we hit a normal release,
    # all older versions are guaranteed normal - stop checking.
    result = []
    found_release = False
    for i, ver in enumerate(versions):
        if found_release:
            result.append(ver)
            continue
        ver_url = releases_url + ver + "/"
        try:
            with urllib.request.urlopen(ver_url, timeout=15) as resp:
                ver_html = resp.read().decode("utf-8")
            # Find subdirectory links: href="name/" (not starting with /)
            subdirs = re.findall(r'href="([^"/][^"]*)/"', ver_html)
            # Filter: keep only simple directory names, exclude parent links
            subdirs = [s for s in subdirs if "/" not in s and s != ".."]

            if "release" in subdirs:
                result.append(ver)
                found_release = True
            else:
                for s in subdirs:
                    if s and s != "..":
                        result.append(f"{ver}_{s}")
        except Exception:
            # If version page unreachable, include as-is
            # (don't set found_release - we can't be sure it's normal)
            result.append(ver)

    print(json.dumps(result))
except Exception as e:
    print(f"Error: failed to fetch Ubuntu version list: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
    )

    cat << EOF
{
  "archs": ["aarch64", "x86_64"],
  "versions": ${versions_json},
  "mirrors": [
    "https://cdimage.ubuntu.com/",
    "https://mirrors.tuna.tsinghua.edu.cn/ubuntu-cdimage/",
    "https://mirrors.aliyun.com/ubuntu-cdimage/",
    "https://mirrors.ustc.edu.cn/ubuntu-cdimage/"
  ]
}
EOF
}

cmd::info() {
    cat << 'EOF'
{
  "name": "ubuntu",
  "desc": "Ubuntu Base"
}
EOF
}

cmd::get() {
    local version="${1:-}" arch="${2:-}" mirror="${3:-}"
    [[ -z $version || -z $arch || -z $mirror ]] && usage

    local arch_pattern
    case "$arch" in
        aarch64) arch_pattern="base-arm64.tar.gz" ;;
        x86_64) arch_pattern="base-amd64.tar.gz" ;;
        *)
            printf "Error: Unsupported arch: %s\n" "$arch" >&2
            return 1
            ;;
    esac

    # Parse combined version: "26.10_snapshot-1" -> base_ver="26.10", subdir="snapshot-1"
    # Plain version "26.04" -> base_ver="26.04", subdir="release"
    local base_ver subdir
    if [[ $version == *_* ]]; then
        base_ver="${version%%_*}"
        subdir="${version#*_}"
    else
        base_ver="$version"
        subdir="release"
    fi

    local sum_url="${mirror}ubuntu-base/releases/${base_ver}/${subdir}/SHA256SUMS"
    local tar_file=$(curl -fsSL --connect-timeout 10 --max-time 30 "$sum_url" | grep "$arch_pattern" | awk '{print $2}' | sed 's/^\*//' | sort -V | tail -1)
    [[ -z $tar_file ]] && {
        printf "Error: No matching tarball found for arch=%s version=%s\n" "$arch" "$version" >&2
        return 1
    }

    local hash_val=$(curl -fsSL --connect-timeout 10 --max-time 30 "$sum_url" | grep "${tar_file}" | awk '{print $1}')
    [[ -z $hash_val ]] && {
        printf "Error: Failed to fetch hash for %s\n" "$tar_file" >&2
        return 1
    }

    local src="${mirror}ubuntu-base/releases/${base_ver}/${subdir}/${tar_file}"

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
