#!/usr/bin/env bash

# shellcheck shell=bash
# shellcheck disable=SC2034

DESC="ArchLinux (mirrors.tuna.tsinghua.edu.cn)"
OPTION_ARCH=("x86_64")
OPTION_VERSIONS=("latest")

distro_init() {
    local hash_url="https://mirrors.tuna.tsinghua.edu.cn/archlinux/iso/latest/sha256sums.txt"
    local target_file="archlinux-bootstrap-x86_64.tar.zst"
    
    SRC="https://mirrors.tuna.tsinghua.edu.cn/archlinux/iso/latest/${target_file}"
    HASH_VAL=$(curl -sL "$hash_url" | grep "$target_file" | awk '{print $1}')
    HASH_CMD="sha256sum"
}
