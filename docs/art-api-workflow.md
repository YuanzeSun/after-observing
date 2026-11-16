# 后续图片制作

2026年11月16日用户决定：后续新增或重绘图像使用OpenAI图片生成API，不再使用账号内置生图，不制作对照图。此决定之后本轮没有提交新的生图请求，也没有做付费测试；已经完成的素材保留。

旧内置批次入口已停用，历史脚本保存在provenance。新工作使用系统图片工具提供的`image_gen.py`正式CLI，遵守该工具的API模式指引；不要另写SDK请求器或在游戏中接入生成API。

制作环境需安装CLI要求的OpenAI Python SDK，并从环境读取`OPENAI_API_KEY`。密钥不写入工程、命令参数、提示词、日志、图片台账或发行包，不把聊天内容作为配置文件。保持官方API地址，默认图像模型`gpt-image-2`。账号工具的内部版本和参数不可完全核实时，不承诺逐像素相同。

编辑图像时，先查看本地参考图；把确切提示词存成单独文本，再调用系统CLI的edit子命令，传入参考文件、model、quality、size和独立输出文件。保留原图，用版本化新文件审阅，通过后再选入canonical素材路径。图像身份、服装、道具、人数、时间和实际游戏显示都要复核。API的透明背景支持与账号工具可能不同，遇到不支持的参数按工具指引处理，不静默切换模型。

本地CLI位置：`$CODEX_HOME/skills/.system/imagegen/scripts/image_gen.py`。项目的正文、素材登记和发行构建均不依赖这条制作环境路径；玩家只使用已生成并随包提供的图像。所有可控的远端下载继续限制为每秒3,000,000字节或更低，不改系统全局网络配置。

接口与模型参数核对：[OpenAI GPT-Image-2](https://developers.openai.com/api/docs/models/gpt-image-2)、[图片生成指南](https://developers.openai.com/api/docs/guides/image-generation)。
