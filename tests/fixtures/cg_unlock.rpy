init 999 python:
    _test.timeout = 40.0
    _test.transition_timeout = .05
    _test.screenshot_directory = os.environ["AO_CG_PATCH_SCREENS"]

label _cg_patch_seed:
    $ choice_facts = {"cg_patch_existing_choice": "preserve me"}
    $ completed_events = {"g01"}
    "存档接续检查。"
    return

testsuite cg_patch:
    testcase locked:
        assert screen "main_menu"
        assert eval len(CGS) == 32 and not persistent.seen_cgs
        assert eval not renpy.list_slots()
        click "回想与鉴赏"
        click "事件插画"
        assert screen "cg_gallery"
        screenshot "locked.png"

    testcase fresh:
        assert screen "main_menu"
        assert eval set(CGS) == set(persistent.seen_cgs)
        assert eval not renpy.list_slots()
        assert eval not persistent.completed_routes and not persistent.completed_chapters
        assert eval not persistent.seen_scenes and not persistent.chapter_contexts
        assert eval persistent.heard_music == {"theme"} and not persistent.seen_photos
        click "读取存档"
        assert screen "load"
        assert text "空存档"
        screenshot "empty-load.png"
        click "返回"
        click "回想与鉴赏"
        click "事件插画"
        assert text "月面的第一处阴影"
        screenshot "unlocked.png"
        click "月面的第一处阴影"
        assert screen "gallery_image"
        click "关闭插画"

    testcase seed:
        assert eval config.version == "1.1"
        $ persistent.seen_cgs = {"s_event01", "legacy_gallery_key"}
        $ persistent.completed_routes = {"haruka"}
        $ persistent.completed_chapters = {"g01"}
        $ persistent.chapter_contexts = {"g01": {"choice_facts": {"prior": "kept"}}}
        $ persistent.seen_photos = {"01_bus_bag"}
        $ persistent.heard_music = {"theme"}
        $ renpy.save_persistent()
        $ preferences.text_cps = 0
        run Start("_cg_patch_seed")
        advance until "存档接续检查。"
        run FilePage("1")
        click "存档"
        run FileSave(1,confirm=False)
        pause .2
        assert eval FileLoadable(1)

    testcase existing:
        assert screen "main_menu"
        assert eval config.version == os.environ["AO_CG_PATCH_VERSION"]
        assert eval set(persistent.seen_cgs) == set(CGS) | {"legacy_gallery_key"}
        assert eval persistent.completed_routes == {"haruka"}
        assert eval persistent.completed_chapters == {"g01"}
        assert eval persistent.chapter_contexts == {"g01": {"choice_facts": {"prior": "kept"}}}
        assert eval persistent.seen_photos == {"01_bus_bag"} and persistent.heard_music == {"theme"}
        assert eval renpy.list_slots() == ["1-1"]
        run FilePage("1")
        run FileLoad(1,confirm=False)
        pause .3
        assert eval choice_facts == {"cg_patch_existing_choice": "preserve me"}
        assert eval completed_events == {"g01"}
        assert eval set(CGS) <= set(persistent.seen_cgs)
