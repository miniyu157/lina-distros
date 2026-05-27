#!/usr/bin/env bash

# shellcheck shell=bash
# shellcheck disable=SC2034

DESC="Kali NetHunter (kali.download)"
OPTION_ARCH=("aarch64")
OPTION_VERSIONS=("nano" "minimal" "full")

distro_init() {
    local arch="$1" variant="$2"

    local tar_file="kali-nethunter-rootfs-${variant}-arm64.tar.xz"
    local sum_url="https://kali.download/nethunter-images/current/rootfs/SHA256SUMS"

    SRC="https://kali.download/nethunter-images/current/rootfs/${tar_file}"
    HASH_VAL=$(curl -fsSL "$sum_url" | grep "${tar_file/-rootfs/-.*rootfs}" | awk '{print $1}')
    HASH_CMD="sha256sum"
    TAR_STRIP=1
}
