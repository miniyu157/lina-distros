仓库简介：
  这是一个存储发行版源的仓库。

文件结构：
  文件夹中的可执行文件，例如 distros/alpine.sh，是发行版小程序，
  发行版小程序需要根据 SPEC.md 实现 options、info、get 子命令。
  小程序的 options、info 等命令只需要在索引部署时的CI流运行一次，由 build_INDEX.py 脚本生成仓库索引时调用。
  build_INDEX.py --version 可以获取规范版本标识，build_INDEX.py [dir...] 即可生成仓库索引到标准输出，部署仓库时通常需要重定向到 INDEX 文件。

SPEC.md 为规范文件。

若需要编写提交信息，请运行 git 命令查看历史的提交信息进行参考，不要使用 --oneline 输出，需要参考多行提交信息。
撰写风格一致的、简明扼要的提交信息，提交暂存区文件。
