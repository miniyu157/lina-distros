#!/usr/bin/env bash

# shellcheck shell=bash
# shellcheck disable=SC1090

set -euo pipefail
shopt -s inherit_errexit 2> /dev/null || true

version() {
    echo "# LINA_DISTRO_INDEX v2"
}

main() {
    [[ ${1:-} == "--version" ]] && {
        version
        return 0
    }

    version
    echo "# <hash>	<path>	<name>	<archs>	<versions>	<desc>"

    shopt -s nullglob
    local file
    for file in distros/*.sh; do
        (
            DESC="" OPTION_ARCH=() OPTION_VERSIONS=()
            source "$file" > /dev/null 2>&1
            IFS=" "
            local archs="${OPTION_ARCH[*]}"
            local versions="${OPTION_VERSIONS[*]}"
            local name
            name=$(basename "$file" .sh)
            local hash
            hash=$(printf '%s\t%s\t%s\t%s' "$name" "$archs" "$versions" "$DESC" | md5sum | cut -d' ' -f1)
            printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$hash" "$file" "$name" "$archs" "$versions" "$DESC"
        )
    done
    shopt -u nullglob
}

main "$@"
