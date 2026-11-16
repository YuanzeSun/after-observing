# GitHub与itch.io发布

## 版本与构建

版本的唯一入口是`game/core.rpy`中的`config.version`。发行文件名、启动器和阅读器跟随它生成，标签必须完全匹配：`1.1`对应`v1.1`，`1.1.1`对应`v1.1.1`。请保留既有`config.save_directory`，不要在普通维护版本中随版本号改存档目录。

CI会运行真实8路径并生成当前源码与运行指纹。Release工作流再执行相同验收，构建Windows/Linux、检查每项包内资源、用包本身做首章/末章与存读档烟测，最后生成离线全文与SHA256SUMS。

只有全部检查通过才上传；上传先进入草稿，全部文件就绪后才按工作流选择公开发布。标签触发会公开，手动触发默认保留草稿。已公开的同版本文件不静默覆盖，修复应提升版本号。

## 存档标识

Ren’Py的无名语句ID含编译时信息，因此不能每次从空缓存随意重建后假定存档一定兼容。初始`save-baseline/`来自先前已经验收的1.1发行包，不含玩家存档；构建开始先校验并恢复这些`.rpyc`，让引擎复用匹配的语句标识。

在GitHub环境中，构建会优先下载上一稳定Release的`save-baseline.zip`，用该Release的SHA256SUMS校验，再恢复标识。每个新Release都附带其实际编译后的下一次基线。原生剧情、事实含义或调用关系发生变化时，仍必须另做旧存档接续验证。

## 启用itch.io

1. 在itch.io创建游戏项目，记下`账号/项目`，例如`your-name/after-observing`。
2. 在GitHub的Actions Secrets中添加`BUTLER_API_KEY`，不要粘贴到Issue、工作流或聊天中。
3. 在Repository Variables设置`ITCH_TARGET`为项目路径。
4. 先手动运行“Sync itch.io”，指定已经公开的GitHub Release标签，检查`windows`与`linux`两个频道。
5. 确认后才将Repository Variable `ITCH_PUBLISH_ENABLED`设为`true`。之后Release工作流会显式调用同步工作流；也保留人工发布Release事件的入口。

GitHub自己的`GITHUB_TOKEN`所产生的事件通常不会再触发另一个工作流，因此自动发布链中使用显式可复用工作流调用，而不是仅依赖`release.published`事件。

同步下载并核对GitHub同版本的所有校验和，解压后把稳定文件路径交给butler，分别推送Windows和Linux目录。Linux可执行位保留；自动生成`.itch.toml`指向正确启动器。butler版本与文件摘要固定，新增版本需审阅更新工具链锁。

目前尚未配置itch账号、项目路径或令牌，自动同步默认关闭。OpenAI制作密钥与itch发布令牌互不相同，CI构建游戏不需要OpenAI密钥。

## 公开材料与边界

GitHub普通仓库只放可构建源码、所需素材和初始标识基线；安装包放Releases。`.build/`、个人存档、SDK、生成缓存、废弃图片与任何密钥不提交。重试工作流后可在Artifact中查看失败日志；大安装包不反复存入短期Actions Artifact。

参考：[GitHub Actions安全](https://docs.github.com/en/actions/reference/security/secure-use)、[GitHub大文件](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)、[Ren’Py发行构建](https://www.renpy.org/doc/html/build.html)、[butler推送](https://itch.io/docs/butler/pushing.html)。
