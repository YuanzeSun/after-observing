# Developer-only, isolated-state regression fixtures. Excluded from player builds.
image cg c_review_probe = Solid("#27394a")

screen c_review_controls():
    zorder 210
    hbox:
        xpos 70 ypos 150 spacing 20
        textbutton "测试回放" action Replay("c_review_replay",scope=replay_scope("s01:chinatsu"),locked=False)
        textbutton "测试音乐" action ShowMenu("music_room")

label c_review_main:
    $ reset_story()
    $ route_id = "chinatsu"
    $ relationship_stage = "dating"
    $ choice_facts = {"g_probe":"keep","c_probe":"main_value"}
    $ completed_events = {"g01","g06"}
    $ chapter("c_review_one")
    $ enter_scene("c_review_main_1", "测试主线第一段", "club", "2026-03-01", "day", [], "quiet")
    show screen c_review_controls
    y "主线第一句，等待测试操作。"
    $ choice_facts["c_probe"] = "second_scene_value"
    y "主线第二句，前情应该保留。"
    call c_review_second from c_review_main_return
    y "主线回到第一段之后。"
    hide screen c_review_controls
    return

label c_review_second:
    $ chapter_finished("c_review_one")
    $ choice_facts["g_second"] = "second_value"
    $ chapter("c_review_two")
    $ enter_scene("c_review_main_2", "测试主线第二段", "roof", "2026-03-02", "night", [], "quiet")
    y "第二章第一句，应在这里建立章节备份。"
    y "第二章第二句。"
    return

label c_review_replay:
    $ chapter("c_review_replay")
    $ enter_scene("c_review_replay_1", "测试回放片段", "club", "2025-12-20", "night", [], "daily")
    $ choice_facts["c_probe"] = "replay_mutation"
    y "回放里的前情来自千夏共享章节，不来自正在暂停的主线。"
    y "回放最后一句，正常return结束。"
    return

label c_review_layers:
    $ reset_story()
    $ chapter("c_review_layers")
    $ enter_scene("c_review_layer_1", "测试图层清理", "club", "2026-03-01", "day", [], "quiet")
    $ CGS["c_review_probe"] = "__test_fixture__"
    $ photo("01_bus_bag")
    y "照片资料测试。"
    $ cg("c_review_probe")
    y "切事件图后，不应仍有照片资料覆盖。"
    $ lunar_reference()
    y "月面资料测试。"
    $ end_cg()
    y "结束事件图后，月面资料不应留在现场画面。"
    $ close_photo()
    hide screen lunar_reference
    $ CGS.pop("c_review_probe",None)
    return

testsuite c_review:
    before testcase:
        if not screen "main_menu":
            run MainMenu(confirm=False)
        $ preferences.text_cps = 0
        $ preferences.afm_enable = False
        $ _test.timeout = 40.0
        $ config.skipping = None

    after testcase:
        $ _test.timeout = 400.0

    testcase file_ui:
        click "读取存档"
        assert screen "load"
        screenshot "c-review-load.png"
        click "返回"
        run Start("c_review_main")
        advance until "主线第一句，等待测试操作。"
        pause .3
        run FilePage("1")
        click "存档"
        assert screen "save"
        run FileSave(1,confirm=False)
        pause .2
        screenshot "c-review-save.png"
        $ review_initial_mtime = renpy.slot_mtime("1-1")
        run FileSave(1,confirm=True)
        assert screen "confirm"
        click "取消"
        assert eval renpy.slot_mtime("1-1") == review_initial_mtime
        pause 1.2
        run FileSave(1,confirm=True)
        assert screen "confirm"
        click "确定"
        pause .3
        assert eval renpy.slot_mtime("1-1") > review_initial_mtime
        run Show("name_slot",slot=slot_label_key(1))
        assert screen "name_slot"
        type "home[raw]"
        pause .3
        screenshot "c-review-naming-before.png"
        click "保存名称"
        pause .2
        $ print("C_REVIEW_NAMES", persistent.slot_names)
        assert eval persistent.slot_names["1:1"] == "home[raw]"
        run Show("name_slot",slot=slot_label_key(1))
        $ renpy.get_screen("name_slot").scope["label"] = "回家[不替换]"
        $ renpy.restart_interaction()
        pause .3
        click "保存名称"
        assert eval persistent.slot_names["1:1"] == "回家[不替换]"
        run FilePage("2")
        assert eval slot_label_key(1) == "2:1" and slot_label_key(1) not in persistent.slot_names
        run FilePage("1")
        screenshot "c-review-named.png"
        run FileDelete(1,confirm=True)
        assert screen "confirm"
        click "取消"
        assert eval FileLoadable(1)
        run FileDelete(1,confirm=True)
        click "确定"
        assert eval not FileLoadable(1)
        click "返回"
        run MainMenu(confirm=False)

    testcase chapter_backup:
        run Start("c_review_main")
        advance until "主线第一句，等待测试操作。"
        pause .3
        assert eval FileLoadable("c_review_one",page="chapter") and not chapter_backup_pending
        advance until "第二章第一句，应在这里建立章节备份。"
        pause .3
        assert eval FileLoadable("c_review_two",page="chapter")
        run SetVariable("route_id","haruka")
        run SetVariable("choice_facts",{})
        run FileLoad("c_review_two",page="chapter",confirm=False)
        assert eval current_chapter == "c_review_two" and current_scene == "c_review_main_2"
        assert eval route_id == "chinatsu" and choice_facts["g_second"] == "second_value"
        assert eval "c_review_one" in completed_events and not chapter_backup_pending
        run MainMenu(confirm=False)

    testcase reset_route:
        run Start("c_review_main")
        advance until "主线第一句，等待测试操作。"
        run SetVariable("completed_events",{"g01","g06","c01","c04","s01","s04"})
        run SetVariable("choice_facts",{"g_probe":"keep","double_star":True,"joined":True,"moon":True,"outreach":"guide","c_01":"old","h_06":"old"})
        run Jump("route_choice")
        advance until screen "choice"
        assert screen "choice"
        assert eval route_id is None and relationship_stage == "interest"
        assert eval choice_facts == {"g_probe":"keep","double_star":True,"joined":True,"moon":True,"outreach":"guide"}
        assert eval completed_events == {"g01","g06"}
        assert eval current_cg is None and active_photo is None and phone_speaker is None and not actor_states
        run MainMenu(confirm=False)

    testcase replay_context:
        $ persistent.chapter_contexts["s01:chinatsu"]={"route_id":"chinatsu","relationship_stage":"interest","choice_facts":{"g_probe":"remembered"},"completed_events":{"g01","g06"}}
        run Start("c_review_main")
        advance until "主线第一句，等待测试操作。"
        $ review_before_context = copy.deepcopy(persistent.chapter_contexts["s01:chinatsu"])
        $ review_before_seen = set(persistent.seen_scenes)
        click "测试回放"
        advance until "回放里的前情来自千夏共享章节，不来自正在暂停的主线。"
        assert eval bool(_in_replay) and route_id == "chinatsu" and relationship_stage == "interest"
        assert eval choice_facts["g_probe"] == "remembered" and choice_facts["c_probe"] == "replay_mutation"
        assert eval not FileLoadable("c_review_replay",page="chapter")
        advance until eval not _in_replay
        assert eval current_scene == "c_review_main_1" and relationship_stage == "dating"
        assert eval choice_facts == {"g_probe":"keep","c_probe":"main_value"}
        assert eval persistent.chapter_contexts["s01:chinatsu"] == review_before_context
        assert eval "c_review_replay_1" not in persistent.seen_scenes
        assert eval renpy.music.get_playing(channel="music") == MUSIC["quiet"]
        click "测试回放"
        advance until "回放里的前情来自千夏共享章节，不来自正在暂停的主线。"
        click "结束回放"
        assert eval not _in_replay and current_scene == "c_review_main_1"
        assert eval choice_facts == {"g_probe":"keep","c_probe":"main_value"}
        run MainMenu(confirm=False)

    testcase music_return:
        run Start("c_review_main")
        advance until "主线第一句，等待测试操作。"
        $ persistent.heard_music.add("daily")
        pause 1.2
        assert eval renpy.music.get_playing(channel="music") == MUSIC["quiet"]
        click "测试音乐"
        assert screen "music_room"
        click "Easy Lemon"
        pause .3
        assert eval renpy.music.get_playing(channel="music") == MUSIC["daily"]
        click "返回"
        pause .3
        assert eval current_music == "quiet"
        $ print("C_REVIEW_MUSIC", current_music, renpy.music.get_playing(channel="music"))
        assert eval renpy.music.get_playing(channel="music") == MUSIC["quiet"]
        run MainMenu(confirm=False)

    testcase layers:
        run Start("c_review_layers")
        advance until "切事件图后，不应仍有照片资料覆盖。"
        assert not screen "story_photo"
        assert eval active_photo is None
        advance until "结束事件图后，月面资料不应留在现场画面。"
        assert not screen "lunar_reference"
        run MainMenu(confirm=False)
