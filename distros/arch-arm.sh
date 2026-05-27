#!/usr/bin/env bash

# shellcheck shell=bash
# shellcheck disable=SC2034

DESC="ArchLinux ARM (os.archlinuxarm.org)"
OPTION_ARCH=("aarch64")
OPTION_VERSIONS=("latest")

distro_init() {
    SRC="http://os.archlinuxarm.org/os/ArchLinuxARM-aarch64-latest.tar.gz"
    HASH_VAL="http://os.archlinuxarm.org/os/ArchLinuxARM-aarch64-latest.tar.gz.md5"
    HASH_CMD="md5sum"
}
