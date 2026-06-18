# 发行版小程序接口及索引规范 V4

## 概述

发行版小程序是一个可执行文件，对外暴露三个子命令：`options`、`info`、`get`。

三个子命令均输出 JSON 到标准输出，格式固定，不允许额外包装层。

---

## 小程序接口

抓取内容时应当减少 HTTP 请求次数。

遇到错误应当打印错误信息到标准错误，然后以非 0 状态码退出。

客户端应当忽略不认识的字段以保证兼容性。

### options

将一个包含 get 子命令可选项的 JSON 对象打印到标准输出。  
仅在 CI 构建统一索引时运行一次，不在客户端高频调用。

*输出示例:*

```json
{
  "archs": ["x86_64", "aarch64", "ppc64le", "s390x"],
  "versions": ["8", "9", "10"],
  "mirrors": [
    "https://dl.rockylinux.org/pub/rocky",
    "https://mirrors.ustc.edu.cn/rocky",
    "https://mirrors.aliyun.com/rockylinux"
  ]
}
```

*注意事项:*

- 所有字段均不得为空数组。
- archs 数组中，推荐将一些架构，例如 arm64、amd64 统一为 aarch64、x86_64 风格，以便下游客户端按需自动选择。
- mirrors 数组中推荐将官方源置于首位。
- version 数组中推荐将顺序输出为从新到旧，靠前的是新版本，靠后的是旧版本。

如果硬编码会导致未来需要持续人工追加新值，则可以动态抓取；如果列表在可预见的未来不需要增删，可以硬编码。

动态抓取时若发生网络错误，必须以非零状态码退出并打印错误信息到 stderr。重试机制由索引编排脚本统一处理，小程序自身无需实现重试或 fallback。

---

### info

将一个包含发行版描述的 JSON 对象打印到标准输出。  
仅在 CI 构建统一索引时运行一次，不在客户端高频调用。

*输出示例:*

```json
{
  "name": "rocky",
  "desc": "Rocky Linux"
}
```

---

### get

接收版本等参数，将一个包含发行版下载信息的 JSON 对象打印到标准输出。

下游客户端通常会拉取统一的仓库索引，将 options() 中预设的选项传入。
因此无需校验参数，除非你想为手动调用添加自定义提示信息。

*用法:* `get <version> <arch> <mirror>`

version、arch、mirror 均为必选的位置参数。
arch: 通常不会传入 arm64、amd64 风格的参数，如果需要在 url 中拼接，应当手动处理映射。若上游镜像固定只有一个 arch，可以忽略参数，抓取时硬编码。

*输出示例:*

```json
{
  "src": "https://dl.rockylinux.org/pub/rocky/10/images/aarch64/Rocky-10-Container-Base.latest.aarch64.tar.xz",
  "ext": {
    "hash_val": "sha256:995350a80651f2867e399196288d17704f13b1035fb78e4bf56ba74a2d7775d7",
    "find": "."
  }
}
```

*字段说明:*

**src** (string, 必选) — 发行版 rootfs 归档文件的下载直链。

**ext** (object, 必选) — 扩展信息对象，客户端应当忽略不认识的字段。

- `ext.hash_val` (string) — 可选值为 `SKIP` 字符串或 `<算法:hash字符串>`。算法遵循小写格式，限定于以下枚举列表，客户端需编码这些算法的解析器。

  ```text
  sha256
  sha512
  b2
  md5
  sha1
  ```

  未来会根据实际需求修订规范，以扩展支持的算法。

- `ext.find` (string | number) — 指示归档中 rootfs 的位置。
  - `"."` 或 `0` — rootfs 位于归档根目录，直接解压即可。
  - 正整数（如 `1`, `2`, `3`）— 需要剥离相应层数的目录前缀（等效于 `tar --strip-components=N`）。
  - 字符串（如 `"./rootfs"`, `"rootfs/"`, `"/path/to/rootfs"`）— rootfs 位于归档内该路径的子目录中。

---

## 仓库索引

JSON 格式的仓库索引，由编排脚本 `build_INDEX.py` 聚合所有小程序的输出生成，供下游客户端统一查询。

### JSON Schema

```json
{
  "version": "v4",
  "entries": [
    {
      "name": "rocky",
      "desc": "Rocky Linux",
      "applet": {
        "file": "distros/rocky.sh",
        "hash": "a1b2c3d",
        "options": {
          "archs": ["x86_64", "aarch64"],
          "versions": ["8", "9", "10"],
          "mirrors": [
            "https://dl.rockylinux.org/pub/rocky",
            "https://mirrors.ustc.edu.cn/rocky"
          ]
        }
      }
    }
  ]
}
```

| 字段 | 类型 | 说明 |
| ------ | ------ | ------ |
| `version` | string | 规范版本标识，当前为 `"v4"` |
| `entries` | array | 发行版条目列表，按文件名排序 |
| `entries[].name` | string | 发行版简称，由小程序的 `info` 输出 |
| `entries[].desc` | string | 发行版描述，由小程序的 `info` 输出 |
| `entries[].applet` | object | 编排元数据，由编排脚本插入 |
| `entries[].applet.file` | string | 小程序文件路径，相对于仓库根目录 |
| `entries[].applet.hash` | string | 小程序文件内容的 SHA256 前 7 位十六进制，用于下游客户端缓存与去重 |
| `entries[].applet.options` | object | 小程序的 `options` 子命令输出，透传不修改 |

### 编排脚本

`build_INDEX.py` 是仓库索引的编排脚本，聚合所有发行版小程序的输出。

小程序出现网络异常或非零退出时，编排脚本自动重试（默认最多 3 次，指数退避）。瞬态故障不应导致索引条目缺失。

若重试耗尽仍未成功，跳过该小程序并打印警告到 stderr，继续处理其余小程序。单个失败不中断整体索引生成。

编排脚本插入 `applet` 元数据字段——`file`（脚本路径）、`hash`（脚本 SHA256 前 7 位）。
其余字段（`name`、`desc`、`archs`、`versions`、`mirrors` 等）由小程序输出透传，不做解读或校验。

---

## CI 流程

仓库索引由 GitHub Actions 自动维护。触发条件：

- `main` 分支上 `distros/*.sh` 或 `build_INDEX.py` 变更时触发。
- 每日 UTC 00:07 定时触发。
- 手动 workflow_dispatch 触发。

**流程：**

1. `build_INDEX.py distros > INDEX.new` — 生成新索引。
2. `diff -q INDEX INDEX.new` — 若无变化则退出，避免空提交。
3. `gen-commit-msg.py` — 比较新旧 INDEX，生成含变更详情的提交信息。
4. `mv INDEX.new INDEX && git add INDEX && git commit && git push` — 提交并推送。

**提交信息格式：**

- 初始构建: `auto: update INDEX (initial build)`
- 无变更: 不做提交
- 有变更，版本号相同: `auto: update INDEX [alpine, ubuntu]`
- 有变更，版本号升级: `auto: update INDEX v2→v3 [alpine, ubuntu]`
- 仅版本号变更: `auto: update INDEX v2→v3`
