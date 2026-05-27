#!/usr/bin/env bash

# shellcheck shell=bash
# shellcheck disable=SC2034

DESC="Alpine Linux (dl-cdn.alpinelinux.org)"
OPTION_ARCH=("aarch64" "x86_64")
OPTION_VERSIONS=("latest-stable")

distro_init() {
    local yaml_url="https://dl-cdn.alpinelinux.org/alpine/${1}/releases/${2}/latest-releases.yaml"
    local yaml_text
    yaml_text=$(curl -fsSL "$yaml_url" 2> /dev/null)
    [[ -z $yaml_text ]] && return 1

    local filename
    filename=$(echo "$yaml_text" | awk '/flavor: alpine-minirootfs/{found=1} found && /^  file: /{print $2; exit}')

    SRC="https://dl-cdn.alpinelinux.org/alpine/${1}/releases/${2}/${filename}"
    HASH_VAL=$(echo "$yaml_text" | awk '/flavor: alpine-minirootfs/{found=1} found && /^  sha256: /{print $2; exit}')
    HASH_CMD="sha256sum"
}
