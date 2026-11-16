# Production inspection only; excluded from every player build.
init python:
    def author_measure_dialogue():
        with open(config.basedir+"/docs/layout-rows.json",encoding="utf-8") as f:
            pages=json.load(f)
        measured=[]
        for size in (32,34,38):
            for row in pages:
                page=Text(row["text"],font="fonts/NotoSansCJKsc-Regular.otf",size=size,line_spacing=10,substitute=False)
                rendered=renpy.render(page,1640,1200,0,0)
                measured.append(dict(row,size=size,height=rendered.height))
        with open(config.basedir+"/docs/dialogue-layout.json","w",encoding="utf-8") as f:
            json.dump({"tested":len(measured),"max_height":max(x["height"] for x in measured),"available_height":225,"overflows":[x for x in measured if x["height"]>225]},f,ensure_ascii=False,indent=2)
        return all(x["height"]<=225 for x in measured)
screen author_sprite_proof(master):
    zorder 240
    add Solid("#506579")
    $ pieces = master.split("_")
    $ actor = pieces[0]
    $ clothing = pieces[1]
    $ actor_pose = "pose"+pieces[2][-1]
    $ carries_camera = "free" not in pieces
    text master xpos 55 ypos 32 size 32 color "#ffffff"
    hbox:
        xpos 25 ypos 125 spacing 10
        for mood in ("normal","smile","puzzled","displeased","shy","sad"):
            vbox:
                xsize 300 spacing 12
                add portrait_for_state(actor,(clothing,mood,actor_pose,carries_camera)) xysize (300,650) fit "contain"
                text mood xalign .5 size 25 color "#ffffff"

screen author_background_proof(keys):
    zorder 240
    add Solid("#13263c")
    grid 2 2:
        xpos 35 ypos 30 spacing 25
        for key in keys:
            vbox:
                xsize 900 spacing 8
                add ("bg "+key) xysize (900,460) fit "contain"
                text key size 25

label author_font_page:
    $ reset_story()
    $ enter_scene("author_font_probe", "最大字号排版检查", "club", "2026-03-06", "day", [("h","uniform","normal")], "quiet")
    $ author_longest = json.load(open(config.basedir+"/docs/layout-rows.json",encoding="utf-8"))[0]["text"]
    y "[author_longest]"
    return

label author_reference_page:
    $ reset_story()
    $ enter_scene("author_reference_probe", "资料与对白排版检查", "club", "2026-03-06", "day", [("h","uniform","normal")], "quiet")
    $ renpy.show_screen(author_reference_name)
    h "先看这张图。看完以后，我们再把刚才没看清的地方对一遍。"
    return

testsuite visual_references:
    before testcase:
        $ preferences.text_cps = 0
    testcase maximum_font:
        $ persistent.dialogue_size = 38
        run Start("author_font_page")
        pause .01 until screen "say"
        pause .2
        assert screen "say"
        assert eval tuple(renpy.get_displayable("say","window").get_placement()[:4]) == (90,735,0,0)
        assert eval tuple(renpy.get_displayable("say","what").get_placement()[2:4]) == (0,0)
        screenshot "maximum-font-dialogue.png"
        run MainMenu(confirm=False)
    testcase science:
        parameter page = ["lunar_reference","eclipse_reference","eyepiece_impression"]
        run SetVariable("author_reference_name",page)
        run Start("author_reference_page")
        pause .01 until screen "say"
        pause .2
        assert screen page
        screenshot f"reference-{page}.png"
        run MainMenu(confirm=False)
    testcase morning_and_night:
        run Show("author_background_proof",keys=["camp_corridor_day","camp_corridor","noodle_shop","noodle_shop_night"])
        screenshot "morning-and-night.png"
        run Hide("author_background_proof")
    testcase revisions:
        parameter key = ["s_event05","s_event07","a_event05","r_event01"]
        run Show("gallery_image",key=key)
        pause .2
        screenshot f"revised-{key}.png"
        run Hide("gallery_image")

testsuite visual_assets:
    testcase dialogue_layout:
        assert eval author_measure_dialogue()
    testcase exhibition:
        run Show("gallery_image",key="c_event05")
        pause .2
        screenshot "exhibition-composition.png"
        run Hide("gallery_image")
    testcase sprites:
        parameter master = ['a_casual_p1_normal', 'a_casual_p2_normal', 'a_uniform_p1_normal', 'a_uniform_p2_normal', 'a_winter_p1_normal', 'a_winter_p2_normal', 'c_casual_p1_normal', 'c_casual_p1_normal_free', 'c_casual_p2_normal', 'c_casual_p2_normal_free', 'c_uniform_p1_normal', 'c_uniform_p1_normal_free', 'c_uniform_p2_normal', 'c_uniform_p2_normal_free', 'c_winter_p1_normal', 'c_winter_p1_normal_free', 'c_winter_p2_normal', 'c_winter_p2_normal_free', 'h_casual_p1_normal', 'h_casual_p2_normal', 'h_uniform_p1_normal', 'h_uniform_p2_normal', 'h_winter_p1_normal', 'h_winter_p2_normal', 'r_casual_p1_normal', 'r_casual_p2_normal', 'r_uniform_p1_normal', 'r_uniform_p2_normal', 'r_winter_p1_normal', 'r_winter_p2_normal']
        run Show("author_sprite_proof",master=master)
        pause .2
        screenshot f"sprites-{master}.png"
        run Hide("author_sprite_proof")
    testcase event_cgs:
        parameter key = ['a_event01', 'a_event02', 'a_event03', 'a_event04', 'a_event05', 'a_event06', 'c_event01', 'c_event02', 'c_event03', 'c_event04', 'c_event05', 'c_event06', 'h_event01', 'h_event02', 'h_event03', 'h_event04', 'h_event05', 'h_event06', 'r_event01', 'r_event02', 'r_event03', 'r_event04', 'r_event05', 'r_event06', 's_event01', 's_event02', 's_event03', 's_event04', 's_event05', 's_event06', 's_event07', 's_event08']
        run Show("gallery_image",key=key)
        pause .2
        screenshot f"cg-{key}.png"
        run Hide("gallery_image")
    testcase backgrounds:
        parameter index = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        run Show("author_background_proof",keys=sorted(BACKGROUNDS)[index*4:index*4+4])
        pause .2
        screenshot f"backgrounds-{index}.png"
        run Hide("author_background_proof")
