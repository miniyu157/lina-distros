#!/usr/bin/env bash

# shellcheck shell=bash
# shellcheck disable=SC2034

DESC="Ubuntu Base (cdimage.ubuntu.com)"
OPTION_ARCH=("aarch64" "x86_64")
OPTION_VERSIONS=("14.04" "16.04" "18.04" "20.04" "22.04" "24.04" "25.10" "26.04")

distro_init() {
    local arch="$1" version="$2"
    local arch_pattern
    case "$arch" in
        aarch64) arch_pattern="base-arm64.tar.gz" ;;
        x86_64) arch_pattern="base-amd64.tar.gz" ;;
        *) return 1 ;;
    esac

    local sum_url="https://cdimage.ubuntu.com/ubuntu-base/releases/${version}/release/SHA256SUMS"
    local tar_file
    tar_file=$(curl -fsSL "$sum_url" | grep "$arch_pattern" | awk '{print $2}' | sed 's/^\*//' | sort -V | tail -1)
    [[ -z $tar_file ]] && return 1

    SRC="https://cdimage.ubuntu.com/ubuntu-base/releases/${version}/release/${tar_file}"
    HASH_VAL=$(curl -fsSL "$sum_url" | grep "${tar_file}" | awk '{print $1}')
    HASH_CMD="sha256sum"
}
