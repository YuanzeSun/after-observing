style default:
    font "fonts/NotoSansCJKsc-Regular.otf"
    size 30
    color "#e8e6e0"
style button:
    background Solid("#233346dc")
    hover_background Solid("#3b5265ef")
    padding (24,14)
    hover_sound "audio/release/ui_hover.wav"
    activate_sound "audio/release/ui_select.wav"
style button_text:
    size 28
    color "#d9e0e6"
    hover_color "#ffffff"
    selected_color "#edca8b"
    insensitive_color "#66717b"
style input:
    color "#e8e6e0"
style bar:
    xsize 600 ysize 18
    left_bar Solid("#c2aa7c")
    right_bar Solid("#3d4a59")
    thumb Solid("#ede3cd")
    thumb_offset 7
style slider is bar
style mainnav_button is button:
    xsize 450 ysize 62 padding (24,10)
    background Solid("#f5f2e9de")
    hover_background Solid("#fffaf0")
style mainnav_button_text is button_text:
    size 27 color "#3c4c5f" hover_color "#172d43"

default persistent.slot_names = {}
default persistent.textbox_opacity = 0.94

screen say(who,what):
    window:
        id "window"
        xpos 90 ypos 735 xsize 1740 ysize 300
        xanchor 0 yanchor 0
        background Solid("#f9f7efef")
        padding (0,0) margin (0,0)
        add Solid("#a1b7c8") ysize 2
        if who:
            text who id "who" xpos 48 ypos 20 xanchor 0 yanchor 0 size 29 color "#6b5944"
        text what id "what" xpos 48 ypos 75 xanchor 0 yanchor 0 xsize 1640 size persistent.dialogue_size line_spacing 10 color "#34465b"
    use quick_menu
    if phone_speaker:
        frame:
            xpos 30 ypos 385 xsize 275 ysize 380
            padding (12,12) background Solid("#172c40ea")
            add portrait(phone_speaker) xysize (250,325) fit "contain"
            text "通话中" size 22 xalign .5 yalign 1.0
    elif speaking_npc and not current_cg and renpy.loadable(speaking_npc):
        frame:
            xpos 25 ypos 380 xsize 270 ysize 385 padding (8,8)
            background Solid("#173049df")
            add speaking_npc xysize (254,369) fit "contain"

screen quick_menu():
    zorder 100
    add Solid("#13263ce8") xpos 1125 ypos 1035 xsize 705 ysize 43
    hbox:
        xpos 1145 ypos 1038 spacing 18
        textbutton "历史" action ShowMenu("history") text_size 21 background None padding (0,0)
        textbutton "回退" action Rollback() text_size 21 background None padding (0,0)
        textbutton "存档" action ShowMenu("save") text_size 21 background None padding (0,0)
        textbutton "读取" action ShowMenu("load") text_size 21 background None padding (0,0)
        textbutton ("自动中" if preferences.afm_enable else "自动") action Preference("auto-forward","toggle") text_size 21 background None padding (0,0)
        textbutton ("快进中" if renpy.is_skipping() else "快进") action Skip() text_size 21 background None padding (0,0)
        textbutton "设置" action ShowMenu("preferences") text_size 21 background None padding (0,0)
        textbutton "帮助" action ShowMenu("help") text_size 21 background None padding (0,0)
    if _in_replay:
        textbutton "结束回放" xpos 30 ypos 1035 text_size 23 action EndReplay(confirm=False)

screen chapter_caption():
    zorder 80
    frame:
        xpos 30 ypos 24 xsize 1240 ysize 58 padding (18,12)
        background Solid("#12253bd9")
        hbox:
            spacing 25
            text "观测结束以后" color "#ead9b4" size 23
            text scene_name size 23
    text current_date xpos 1585 ypos 35 size 22 color "#e7e8df"
    if completed_events or current_scene:
        textbutton "观测手记" xpos 1660 ypos 91 text_size 22 action Show("notebook")

screen choice(items):
    modal True zorder 150
    add Solid("#0a15278c")
    vbox:
        xalign .5 yalign .44 spacing 24
        text scene_name xalign .5 color "#e7d7b6" size 26
        for item in items:
            textbutton item.caption action item.action xsize 1160 yminimum 88 text_xalign .5
    use quick_menu

screen main_menu():
    tag menu
    if renpy.loadable("images/v11/title.png"):
        add Transform("images/v11/title.png",xysize=(1920,1080),fit="cover")
    else:
        add "bg roof"
    add Solid("#102039a8") xpos 0 xsize 725
    text "AFTER OBSERVING" xpos 120 ypos 165 size 24 color "#bbc9d7" kerning 6
    text "观测结束以后" xpos 110 ypos 228 size 84 color "#f1e8d7"
    text "十月相遇，四月再见。" xpos 120 ypos 343 size 27 color "#cdd6df"
    vbox:
        style_prefix "mainnav"
        xpos 120 ypos 420 spacing 12
        textbutton "开始阅读" action Start()
        textbutton "继续阅读" action Continue()
        textbutton "读取存档" action ShowMenu("load")
        textbutton "回想与鉴赏" action ShowMenu("memories")
        textbutton "阅读设置" action ShowMenu("preferences")
        textbutton "操作帮助" action ShowMenu("help")
        textbutton "制作与素材署名" action ShowMenu("credits")
        textbutton "退出" action Quit(confirm=False)
    text "1.1 / 四条独立路线" xpos 120 ypos 1020 size 21 color "#c0cbd7"

screen menu_shell(title):
    add "bg roof"
    add Solid("#102137ec")
    text title xpos 110 ypos 65 size 48 color "#eddbb8"
    add Solid("#6a7c8b") xpos 110 ypos 155 xsize 1700 ysize 1
    textbutton "返回" xpos 1665 ypos 62 action Return()
    if not main_menu:
        textbutton "主菜单" xpos 1480 ypos 62 action MainMenu(confirm=True)

screen save():
    tag menu
    use file_slots("保存进度",True)
screen load():
    tag menu
    use file_slots("读取进度",False)
screen file_slots(title,saving):
    use menu_shell(title)
    grid 3 2:
        xpos 140 ypos 215 spacing 32
        for slot in range(1,7):
            vbox:
                spacing 7
                button:
                    xsize 520 ysize 285
                    action (FileSave(slot,confirm=True) if saving else FileLoad(slot,confirm=True))
                    sensitive not _in_replay or not saving
                    vbox:
                        spacing 10
                        add FileScreenshot(slot) xysize (464,186)
                        text FileTime(slot,format="%Y-%m-%d %H:%M",empty="空存档") size 20
                        text persistent.slot_names.get(slot_label_key(slot),FileSaveName(slot)) size 20 xsize 465 substitute False
                hbox:
                    spacing 12
                    textbutton "命名" action Show("name_slot",slot=slot_label_key(slot)) text_size 19 sensitive FileLoadable(slot)
                    textbutton "删除" action FileDelete(slot,confirm=True) text_size 19 sensitive FileLoadable(slot)
    hbox:
        xpos 140 ypos 958 spacing 16
        textbutton "自动备份" action FilePage("auto") text_size 23
        textbutton "快速" action FilePage("quick") text_size 23
        for page in range(1,9):
            textbutton str(page) action FilePage(page) text_size 23
        if not saving:
            textbutton "章节备份" action ShowMenu("chapter_saves") text_size 23
            textbutton "结局记录" action ShowMenu("ending_saves") text_size 23
    if _in_replay:
        text "回放期间不能覆盖主线进度。" xpos 990 ypos 974 size 23 color "#d6c5a8"

screen name_slot(slot):
    modal True zorder 280
    default label = persistent.slot_names.get(slot,"")
    add Solid("#051225bb")
    frame:
        xalign .5 yalign .45 xsize 1050 padding (45,40)
        background Solid("#25364b")
        vbox:
            spacing 28
            text "给这个存档槽起个名字" size 32
            input value ScreenVariableInputValue("label") length 24 xsize 900
            hbox:
                spacing 24
                textbutton "保存名称" action [SetDict(persistent.slot_names,slot,label),Hide("name_slot")]
                textbutton "取消" action Hide("name_slot")

screen chapter_saves():
    tag menu
    use menu_shell("章节备份")
    viewport:
        xpos 140 ypos 210 xsize 1640 ysize 775 mousewheel True draggable True
        vbox:
            spacing 12
            for key,info in CHAPTERS.items():
                if key.startswith("s"):
                    for route in ROUTES:
                        textbutton (info["title"]+" / "+route.name) action FileLoad(key+"-"+route.id,page="chapter",confirm=True) sensitive FileLoadable(key+"-"+route.id,page="chapter") xsize 1530
                else:
                    textbutton info["title"] action FileLoad(key,page="chapter",confirm=True) sensitive FileLoadable(key,page="chapter") xsize 1530

screen ending_saves():
    tag menu
    use menu_shell("结局记录")
    vbox:
        xpos 145 ypos 230 spacing 30
        for route in ROUTES:
            textbutton (route.name+" / 四月，再见") action FileLoad("ending-"+route.id,page="ending",confirm=True) sensitive FileLoadable("ending-"+route.id,page="ending") xsize 1470

screen preferences():
    tag menu
    use menu_shell("阅读设置")
    hbox:
        xpos 145 ypos 215 spacing 170
        vbox:
            spacing 22
            text "文字速度" size 29
            bar value Preference("text speed")
            text "自动播放等待" size 29
            bar value Preference("auto-forward time")
            text "字号" size 29
            hbox:
                spacing 20
                for size in (32,34,38):
                    textbutton str(size) action SetField(persistent,"dialogue_size",size) selected persistent.dialogue_size==size
            hbox:
                spacing 20
                textbutton "窗口" action Preference("display","window")
                textbutton "全屏" action Preference("display","fullscreen")
            textbutton "仅快进已读" action Preference("skip","seen")
            text "选项出现时停止自动与快进。" size 23 color "#b8c7d6"
        vbox:
            spacing 22
            text "音乐" size 29
            bar value Preference("music volume")
            text "效果音" size 29
            bar value Preference("sound volume")
            text "环境音" size 29
            bar value Preference("mixer ambient volume")
            textbutton "全部静音" action Preference("all mute","toggle")

screen history():
    tag menu
    use menu_shell("阅读历史")
    viewport:
        xpos 140 ypos 205 xsize 1630 ysize 790 mousewheel True draggable True yinitial 1.0
        vbox:
            spacing 25
            for entry in _history_list:
                vbox:
                    spacing 5
                    if entry.who:
                        text entry.who size 24 color "#dbc498" substitute False
                    text entry.what size 29 xsize 1600 substitute False

screen help():
    tag menu
    use menu_shell("操作帮助")
    vbox:
        xpos 145 ypos 220 spacing 25
        text "点击、空格、Enter：继续阅读" size 30
        text "滚轮向上、Page Up：回退" size 30
        text "右键、Esc：打开或关闭菜单" size 30
        text "Ctrl：快进已读部分；H：暂时隐藏界面；F：全屏切换" size 28
        text "章节自动连续，选项不会替你选择。随时可以保存进度。" size 28
        text "回想中的章节使用实际阅读前情；结束回放回到原处。" size 28
        text "四条路线均可首次进入，共通篇末会明确选择继续相处的人。" size 25 color "#b7c5d4"

screen confirm(message,yes_action,no_action):
    modal True zorder 300
    add Solid("#051225bd")
    frame:
        xalign .5 yalign .45 xsize 1120 padding (48,45) background Solid("#26364b")
        vbox:
            spacing 35
            text message size 30 xsize 1000
            hbox:
                spacing 25
                textbutton "确定" action yes_action
                textbutton "取消" action no_action
screen notify(message):
    zorder 270
    frame:
        xpos 55 ypos 105 padding (25,15) background Solid("#233b53ec")
        text message size 24
    timer 3.0 action Hide("notify")

screen notebook():
    modal True zorder 220
    add Solid("#071327b5")
    frame:
        xalign .5 yalign .45 xsize 1360 ysize 850 padding (45,35) background Solid("#e7e2d6")
        vbox:
            spacing 22
            text "观测手记" color "#293c4e" size 38
            viewport:
                xsize 1250 ysize 640 mousewheel True draggable True
                vbox:
                    spacing 20
                    for key in sorted(completed_events):
                        text CHAPTERS.get(key,{}).get("title",key) size 28 color "#33495c"
                    if "double_star" in choice_facts:
                        text "10/24：第一次在目镜里辨出两颗不同颜色的点。" size 26 color "#33495c"
                    if "moon" in choice_facts:
                        text "11/28：明暗边界附近的阴影更清楚；镜中方向不能直接当作纸图方向。" size 26 color "#33495c" xsize 1150
                    if "s01" in completed_events:
                        text "12/20—21：合宿的记录包含看清的、没找到的和一直在等云的部分。" size 26 color "#33495c" xsize 1150
                    if "s04" in completed_events:
                        text "3/21：活动按天空条件调整；来过的人、器材和收场都留在记录里。" size 26 color "#33495c" xsize 1150
                    text "星空背景用于演出，观测资料与摄影来源见素材署名。" size 24 color "#657482"
            textbutton "合上手记" action Hide("notebook") xalign 1.0
    key "game_menu" action Hide("notebook")

screen story_photo(key):
    zorder 85
    frame:
        xpos 420 ypos 55 xsize 1080 ysize 720 padding (8,8) background Solid("#e7e1d3")
        add ("images/release/photo_"+key+".png") xysize (1064,704) fit "contain"
    textbutton "收起照片" xpos 1580 ypos 70 text_size 22 action Function(close_photo)

screen lunar_reference():
    zorder 86
    add Solid("#050c18f5") ysize 735
    add "images/v06/moon_20251128_0900utc.jpg" xpos 635 ypos 5 xysize (650,650)
    text "2025-11-28 18:00 JST / 北向上参考图" xpos 120 ypos 665 size 23
    text "NASA’s SVS / Ernie Wright / LRO" xpos 120 ypos 700 size 21 color "#b5c5d6"
    textbutton "收起参考图" xpos 1570 ypos 65 action Hide("lunar_reference") text_size 23

screen eyepiece_impression():
    zorder 86
    add Solid("#02050b") ysize 735
    add "images/eyepiece_field.svg" xysize (1920,690) fit "contain"
    text "目镜印象示意" xpos 100 ypos 698 size 21 color "#a2b3c4"

screen eclipse_reference():
    zorder 86
    add Solid("#091426") ysize 735
    text "2026年3月3日 / 皆既月食过程示意" xpos 120 ypos 55 size 34 color "#e6d5b6"
    add "images/eclipse_timeline.svg" xpos 160 ypos 120 xysize (1600,450)
    hbox:
        xpos 210 ypos 570 spacing 90
        for time,label in [("18:50","偏食开始"),("20:04","全食开始"),("20:34","食甚"),("21:03","全食结束"),("22:18","偏食结束")]:
            vbox:
                xsize 225 spacing 10
                text time xalign .5 size 28
                text label xalign .5 size 24 color "#c0cfde"
    text "时刻为JST约数，来源：国立天文台。示意图不表示真实比例与亮度。" xpos 120 ypos 690 size 23 color "#aebfd0"
    textbutton "收起资料页" xpos 1580 ypos 55 action Hide("eclipse_reference") text_size 22

screen photograph_zoom(key):
    modal True zorder 245
    add Solid("#081327f2")
    add ("images/release/photo_"+key+".png") xalign .5 yalign .45 xysize (1400,900) fit "contain"
    textbutton "关闭照片" xpos 1635 ypos 970 action Hide("photograph_zoom")
    key "game_menu" action Hide("photograph_zoom")

screen memories():
    tag menu
    use menu_shell("回想与鉴赏")
    hbox:
        xpos 140 ypos 195 spacing 24
        textbutton "事件插画" action ShowMenu("cg_gallery")
        textbutton "已读章节" action ShowMenu("chapter_gallery")
        textbutton "摄影作品" action ShowMenu("photo_gallery")
        textbutton "音乐鉴赏" action ShowMenu("music_room")
    vbox:
        xpos 145 ypos 365 spacing 30
        for route in ROUTES:
            text (route.name+" / "+("已读完" if route.id in persistent.completed_routes else "未读完")) size 32 color route.color
    text "已读内容会逐步收录。回放不覆盖当前主线进度。" xpos 145 ypos 900 size 26 color "#b9c7d4"

screen cg_gallery():
    tag menu
    use menu_shell("事件插画")
    viewport:
        xpos 130 ypos 210 xsize 1700 ysize 770 mousewheel True draggable True
        vpgrid:
            cols 4 spacing 20
            for key in CG_ORDER:
                button:
                    xsize 400 ysize 260 padding (10,10)
                    action Show("gallery_image",key=key)
                    sensitive key in persistent.seen_cgs
                    vbox:
                        spacing 8
                        if key in persistent.seen_cgs:
                            add ("cg "+key) xysize (380,213)
                        else:
                            add Solid("#1c2d41") xysize (380,213)
                        text (CG_TITLES[key] if key in persistent.seen_cgs else "尚未读到") size 22
screen gallery_image(key):
    modal True zorder 245
    add ("cg "+key)
    textbutton "关闭插画" xpos 1630 ypos 970 action Hide("gallery_image")
    key "game_menu" action Hide("gallery_image")

screen chapter_gallery():
    tag menu
    use menu_shell("已读章节")
    viewport:
        xpos 140 ypos 205 xsize 1640 ysize 775 mousewheel True draggable True
        vbox:
            spacing 12
            for key,title,memory in replay_entries():
                textbutton title action Replay(key,scope=replay_scope(memory),locked=memory not in persistent.completed_chapters) xsize 1550

screen photo_gallery():
    tag menu
    use menu_shell("摄影作品")
    if not persistent.seen_photos:
        text "读到的作品会随剧情收在这里。" xpos 145 ypos 245 size 29 color "#c3cfd9"
    viewport:
        xpos 130 ypos 210 xsize 1680 ysize 770 mousewheel True draggable True
        vpgrid:
            cols 4 spacing 20
            for key in sorted(persistent.seen_photos):
                button:
                    xsize 395 ysize 260
                    action Show("photograph_zoom",key=key)
                    vbox:
                        add ("images/release/photo_"+key+".png") xysize (345,195) fit "contain"
                        text PHOTO_TITLES.get(key,"作品照片") size 21

screen music_room():
    tag menu
    use menu_shell("音乐鉴赏")
    viewport:
        xpos 140 ypos 210 xsize 1650 ysize 770 mousewheel True draggable True
        vbox:
            spacing 14
            for key,path in MUSIC.items():
                if key != "night":
                    textbutton (MUSIC_TITLES.get(key,key) if key in persistent.heard_music else "尚未听到") action Play("music",path) sensitive key in persistent.heard_music xsize 1450

screen credits():
    tag menu
    use menu_shell("制作与素材署名")
    viewport:
        xpos 145 ypos 210 xsize 1620 ysize 775 mousewheel True draggable True
        vbox:
            spacing 22
            text "观测结束以后 / 1.1" size 42 color "#eddbb8"
            text "故事、程序与制作：项目创作者与 Codex 协作" size 27
            text "图像：OpenAI imagegen。提示词、参考与原图在工程素材台账保存。" size 26 xsize 1550
            text "音乐：Kevin MacLeod (incompetech.com) / CC BY 4.0" size 28
            text "完整曲目、来源与加工记录见发行包 LICENSES。" size 26
            for title in MUSIC_TITLES.values():
                text title size 24
            textbutton "Creative Commons Attribution 4.0" action OpenURL("https://creativecommons.org/licenses/by/4.0/")
            text "音效与环境音：本项目原创程序声音设计。" size 26
            text "字体：Noto Sans CJK SC / SIL Open Font License 1.1" size 26
            text "月面参考：NASA’s SVS / Ernie Wright / LRO" size 26
            text "引擎：Ren’Py 8.6.0；许可随包提供。" size 26

screen game_ending():
    modal True
    add ("cg "+ROUTE_BY_ID[route_id].prefix+"_event06")
    add Solid("#102137cf")
    vbox:
        xalign .5 yalign .48 spacing 25
        text "观测结束以后" size 62 color "#eddbb8" xalign .5
        text (route_name()+" / 四月，再见") size 36 xalign .5
        text "这条路线已读完。" size 27 color "#c3cfdb" xalign .5
        textbutton "保存结局进度" action FileSave("ending-"+route_id,page="ending",confirm=True) xalign .5
        textbutton "回想与鉴赏" action ShowMenu("memories") xalign .5
        textbutton "重选另一条路线" action Jump("route_choice") xalign .5
        textbutton "返回主菜单" action MainMenu(confirm=False) xalign .5
