# Real story navigation checks. Poll for the first Say after each choice without
# dismissing it; a screen may not exist yet while Start/enter_scene is dissolving.
testsuite story_navigation:
    before testcase:
        if not screen "main_menu":
            run MainMenu(confirm=False)
        $ preferences.text_cps = 0
        $ _test.timeout = 120.0
    testcase opening_rollback:
        run Start("start")
        advance until screen "choice"
        click text "先把灰盒的扣件再检查一遍。"
        pause .01 until eval choice_facts.get("g01_carry")=="case" and renpy.get_screen("say")
        assert eval choice_facts.get("g01_carry")=="case"
        run Rollback(force=True)
        pause .01 until screen "choice"
        assert eval "g01_carry" not in choice_facts
        click text "帮佐伯把饮料先分到桌上。"
        pause .01 until eval choice_facts.get("g01_carry")=="drink" and renpy.get_screen("say")
        assert eval choice_facts.get("g01_carry")=="drink"
        screenshot "story-rollback-alternate.png"
        run MainMenu(confirm=False)
    testcase route_rollback:
        run Start("route_choice")
        pause .01 until screen "choice"
        assert eval route_id is None
        click text "约千夏下一次两个人见面。"
        pause .01 until eval route_id=="chinatsu" and current_chapter=="c01" and renpy.get_screen("say")
        assert eval route_id=="chinatsu" and current_chapter=="c01"
        run Rollback(force=True)
        pause .01 until screen "choice"
        assert eval route_id is None
        click text "约灯里下一次两个人见面。"
        pause .01 until eval route_id=="akari" and current_chapter=="a01" and renpy.get_screen("say")
        assert eval route_id=="akari" and current_chapter=="a01"
        assert eval not any(k.startswith("c_") for k in choice_facts)
        screenshot "story-route-switch.png"
        run MainMenu(confirm=False)
