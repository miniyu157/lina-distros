#!/usr/bin/env bash

# shellcheck shell=bash
# shellcheck disable=SC1090

set -euo pipefail
shopt -s inherit_errexit 2> /dev/null || true

version() {
    echo "# LINA_DISTRO_INDEX v1"
}

main() {
    [[ ${1:-} == "--version" ]] && {
        version
        return 0
    }

    version
    echo "# <path> <arch...> <version...>  # <description>"

    shopt -s nullglob
    local file
    for file in distros/*.sh; do
        (
            DESC="" OPTION_ARCH=() OPTION_VERSIONS=()
            source "$file" > /dev/null 2>&1
            IFS=" "
            echo "${file},${OPTION_ARCH[*]},${OPTION_VERSIONS[*]}  # ${DESC}"
        )
    done
    shopt -u nullglob
}

main "$@"
