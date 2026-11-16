label main_menu:
    $ renpy.music.play("audio/release/theme.ogg",channel="music",fadein=1.0,if_changed=True)
    $ persistent.heard_music.add("theme")
    call screen main_menu
    return

label start:
    $ reset_story()
    call g01 from flow_g01
    $ chapter_finished("g01")
    call g02 from flow_g02
    $ chapter_finished("g02")
    call g03 from flow_g03
    $ chapter_finished("g03")
    call g04 from flow_g04
    $ chapter_finished("g04")
    call g05 from flow_g05
    $ chapter_finished("g05")
    call g06 from flow_g06
    $ chapter_finished("g06")
    jump route_choice

label route_choice:
    $ reset_route_progress()
    $ current_chapter = "g06"
    if current_scene != "g06_phone":
        $ enter_scene("g06_phone", "下一次想见的人", "bedroom", "2025-11-30", "night", [], "quiet")
    menu:
        "约遥下一次两个人见面。":
            $ route_id = "haruka"
        "约千夏下一次两个人见面。":
            $ route_id = "chinatsu"
        "约凛下一次两个人见面。":
            $ route_id = "rin"
        "约灯里下一次两个人见面。":
            $ route_id = "akari"
    $ relationship_stage = "interest"
    jump route_flow

label route_flow:
    $ flow_index = 0
    while flow_index < len(ROUTE_SCHEDULES[route_id]):
        $ next_chapter = ROUTE_SCHEDULES[route_id][flow_index]
        call expression next_chapter from route_event_return
        $ chapter_finished(next_chapter)
        $ flow_index = ROUTE_SCHEDULES[route_id].index(next_chapter) + 1
    $ persistent.completed_routes.add(route_id)
    hide screen chapter_caption
    stop ambient fadeout 1.5
    play music "audio/release/ending.ogg" fadein 1.5
    call screen game_ending
    return
