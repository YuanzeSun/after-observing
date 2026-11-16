# 1.1 写作与运行约定

## 后续美术制作偏好（2026-11-16）

用户指定：后续新增或重绘图片改用 OpenAI 图片生成 API，不再使用账号内置图片生成，不制作对照图。制作时使用环境提供的 OPENAI_API_KEY，不能把密钥写进工程、提示词、日志或发行包；图像在制作阶段生成，玩家游戏不调用 API。默认图像模型为 gpt-image-2，实际请求与参数如实记录，不能声称无法核实的内部构建完全一致。现有已完成素材保留，用户未要求全量重画。API 制作时遵循现有图片 CLI 的工作流与每秒3,000,000字节的可控下载限制。

本工程为独立四线新版，目标40–60万实际可达正文字符；没有1.0存档迁移。不要修改原outputs/author-prototype。全部正文用原生.rpy，不用模板批量填充，不把共通重复计数。每条个人线95,000–110,000字符，十章，每章可以含多日/多个场景；篇幅来自具体事件、对白、行动、幽默和亲密，不能来自重复解释。

## 标签与时间

共通g01..g06：2025-10-24到11-30；分线11月底。个人h/c/r/a01..10。所有章节label以return结束，由主流程调用。01十二月上旬；02十二月中旬；之后共享s01十二月20–21合宿、s02一月5日冬季试办；03一月10日(千夏)/11日(其余)；04一月25日前后告白；05二月7–8日；06二月18–22日；共享s03三月6日毕业；07三月9日前后；08三月15日前后；共享s04三月21日公开观测；09三月22–31日；10四月6日。

共享章节归root，不在个人线复写整个合宿/毕业/公开观测。个人线可以写前后心情与私人相处，不能改写共享事件。第四章确认交往：`$ relationship_stage = "dating"`；不要把此前的人物写成已交往。称呼和亲密随关系改变。

## 原生脚本接口

```
label h01:
    $ chapter("h01")
    $ enter_scene("h01_01", "借书箱旁的空位", "library", "2025-12-06", "day", [("h","casual","normal")], "haruka")
    h "……"
    y "……"
    $ expr("h", "shy")
    "……"
    menu:
        "具体行动一。":
            $ choice_facts["h_01"] = "value_one"
            y "……"
        "具体行动二。":
            $ choice_facts["h_01"] = "value_two"
            y "……"
    return
```

`chapter(id)`仅设章节与自动备份。enter_scene参数必须是字面量，工具用AST提取稳定场景目录。每个不同场景用唯一ID。参数顺序：id、标题、背景、ISO日期、day/evening/night、演员元组列表、音乐；可选weather="rain"、camera=False、phone="h"。进屋穿脱衣服由作者明确指定，不能随背景猜制服/便服。演员h/c/r/a；元组(who,outfit,emotion)，可选第四项pose1/pose2。outfit uniform/winter/casual；emotion normal/smile/puzzled/displeased/shy/sad。

`expr(who,emotion,pose=None)`；`cg("h_event01")`到06（每线六张事件图），`end_cg()`恢复当前场景；`photo("01_bus_bag")`展示作品；`close_photo()`收起。`play sound "audio/release/paper.wav"`等原生语句可用。

背景：club,roof,library,platform,platform_day,road_evening,road_day,cafe,arcade,bookshop,corridor,bedroom,kitchen,riverside,camp_room,camp_yard,camp_day,workshop,train_day,train_night,repair_room,classroom,stairwell,school_gate,station_hall。新增背景先通知root登记，不能临时引用无关图顶替。

音乐：theme,club,daily,night,quiet,tender,ending,haruka,chinatsu,rin,akari,playful,waiting,rain,distance,resolve,warm。各章不必切太多音乐，enter_scene同曲不重播。

说话人y/h/c/r/a、o冈本、m森田、d大野、z野崎、t田边、n中村、p水野、pc摄影教师。其他人可用`"店员" "对白"`原生双字符串，不必给一次性人物新增全局角色。

每条个人线六处二选一，`choice_facts["h_01"]`等保存，后面有实际回声；不引入隐藏好感、攻略锁或突然坏结局。分线只由主流程的明确选择决定。不要在私人线调用共享章节或开始/结局屏幕。

## 文风与审核

中文自然，日式背景依靠活动和生活细节。人物可以偏心、吃醋、逞强、犯错；不要让每场摩擦都被一次完整而漂亮的沟通解决。至少让情绪拐点当面发生，少用“她说……我说……”转述整场谈话。可以安静，但不能同一人物每章重复一套道理。旁白段落尽量不超过90字符，超过必须按实际页面检查拆分。

每个场景需有人在做具体事情，有与上一场不同的可读价值；不是每场都必须推动工作，可有纯粹好笑、心动、陪伴和无所事事。允许复用重修的1.0好段落，不能通过旧稿拼接和模板制造十万字。

各代理只写自己拥有的路线和进度文档，避免共享文件冲突。实际字符统计用源脚本Say节点/实际导出，不统计注释、菜单、标题和代码。
