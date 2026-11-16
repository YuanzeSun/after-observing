# 开发与构建

[![CI](https://github.com/YuanzeSun/after-observing/actions/workflows/ci.yml/badge.svg)](https://github.com/YuanzeSun/after-observing/actions/workflows/ci.yml)

![四位女主与黄昏的校园](game/images/v11/title.png)

一部全年龄高中天文社恋爱视觉小说。高桥悠介因为一张观测会海报走进部室，和藤野遥、小原千夏、佐伯凛、朝仓灯里一起筹备春季公开观测。收好器材以后，还有想一起走的那段路。

四条独立路线均可首次进入。故事包含50章、约43.6万正文字符；共通与共享内容不重复计数，单次路线不会读到全部分支。

## 下载游玩

请到 [Releases](https://github.com/YuanzeSun/after-observing/releases) 下载 Windows 或 Linux 发行包。完整解压后启动包内游戏，保留 `game`、`lib` 等目录；不需要另装Python、Ren’Py或下载另一个压缩包。

发行时同时提供单文件离线全文、校验和、验收证据与存档标识基线。itch.io 地址确定后会在这里补上。

## 源码与素材

本仓库包含运行和构建所需的全部游戏素材，没有Git LFS或私有资源下载步骤。游戏本身不调用生成API，也不需要任何API密钥。剧情、图像、音乐、字体与第三方组件的授权分别见 [LICENSING.md](LICENSING.md)。

- `game/story/`：唯一正式正文，原生Ren’Py章节。
- `game/data/`：章节、场景、立绘、CG、摄影作品和音乐登记。
- `game/images/`、`audio/`、`fonts/`：完整发行素材，已去除废弃迭代图。
- `save-baseline/`：最初1.1发行版的编译语句标识，供存档接续使用，不是个人存档。
- `tools/`：源码检查、真实通关记录、构建、校验、离线阅读器和发布工具。

## 本地构建

自动化验收和发行使用Linux、Python3.12与锁定的Ren’Py8.6.0。源码可在Ren’Py Launcher载入；以下命令会下载并校验完整SDK，生成Windows和Linux包。

```sh
python3 -m venv .venv
. .venv/bin/activate
python tools/ci.py sdk
python tools/ci.py deps
python tools/ci.py baseline
python tools/ci.py static
xvfb-run -a python tools/ci.py native
xvfb-run -a python tools/ci.py build
```

需要系统的Xvfb与常规图形/音频库。已有SDK可设置`RENPY_SDK`；工作目录和输出可分别用`AO_WORK`、`AO_DIST`覆盖，默认`.build/`和`dist/`。所有直接依赖下载限制在3,000,000字节/秒内，SDK、Python依赖和butler均有固定校验值。

## CI/CD

- 推送`main`或提交PR：检查正文与素材，真实执行四线各两种选法，并验证菜单、存读档、回退、回放与版面。失败日志作为短期Artifact保存。
- 推送与游戏版本一致的标签（当前`v1.1`）：重新验收、构建、包内运行和校验，再上传完整文件并发布GitHub Release。
- 手动运行Release工作流：可选分支/提交，默认生成草稿，便于先审阅。
- itch.io：已配置独立同步工作流，默认不启用自动推送。详见 [发布文档](docs/PUBLISHING.md)。

完整通关必须来自真实引擎运行；字数不统计菜单、代码、注释或未注册标签。发行守卫拒绝缺页、缺结局、素材缺失、过期运行证据和版本标签不匹配。Linux包使用自己的启动器与运行库做烟测；这不替代真实Windows设备上的显示缩放、输入法和硬件验收。

## 后续开发

先阅读 [AUTHORING.md](AUTHORING.md)、[人物与时间约定](docs/canon.md) 和 [下一版安排](docs/next-version.md)。章节使用稳定ID，已选事实与回放前情分开；保留存档目录，构建前恢复上一稳定版的编译标识。改写既有剧情后仍需实际读档回归，标识基线不是任意改动都兼容的保证。

后续新增或重绘图片使用OpenAI图片生成API，现有素材保留；制作密钥仅存在制作环境，不提交到仓库或发行包。
