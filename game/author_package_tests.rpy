# Developer-only acceptance fragment. Injected into an extracted Linux package;
# it is excluded from every delivered archive and never changes story scripts.
default package_heroine = "haruka"

init python:
    import os, json, copy, sys
    PACKAGE_CAPTIONS={"haruka":"约遥下一次两个人见面。","chinatsu":"约千夏下一次两个人见面。","rin":"约凛下一次两个人见面。","akari":"约灯里下一次两个人见面。"}
    PACKAGE_PREFIXES={"haruka":"h","chinatsu":"c","rin":"r","akari":"a"}
    PACKAGE_FIXTURES={}
    if os.environ.get("AO_PACKAGE_FIXTURES"):
        with open(os.environ["AO_PACKAGE_FIXTURES"],encoding="utf-8") as f:
            PACKAGE_FIXTURES=json.load(f)
    if os.environ.get("AO_PACKAGE_SCREENSHOTS"):
        _test.screenshot_directory=os.environ["AO_PACKAGE_SCREENSHOTS"]
    def package_visible_first(heroine):
        screen=renpy.get_screen("say")
        return (screen is not None and store.route_id==heroine and
                store.current_chapter==PACKAGE_PREFIXES[heroine]+"01" and
                screen.scope.get("what")==PACKAGE_FIXTURES[heroine]["first"]["text"])
    def package_rpa_visible(heroine):
        who=PACKAGE_PREFIXES[heroine]
        key=sprite_key(who,store.actor_states[who])
        path=SPRITES[key]["path"]
        return renpy.loadable(path) and not os.path.isfile(os.path.join(config.gamedir,path)) and renpy.showing("actor_"+who)
    def package_record(phase,heroine):
        row={"phase":phase,"route":heroine,"chapter":store.current_chapter,
             "scene":store.current_scene,"facts":dict(store.choice_facts),
             "completed_events":sorted(store.completed_events),
             "relationship_stage":store.relationship_stage,
             "completed_routes":sorted(persistent.completed_routes),
             "runtime":sys.executable,"renpy_module":renpy.__file__,
             "rpa_exists":os.path.isfile(os.path.join(config.gamedir,"assets.rpa"))}
        with open(os.environ["AO_PACKAGE_RECORDS"],"a",encoding="utf-8") as f:
            f.write(json.dumps(row,ensure_ascii=False)+"\n")
    def package_enter_last_chapter():
        # Resume the actual compiled route loop at its While node, after setting
        # the recorded pre-chapter state. This does not interpret a second story.
        fixture=PACKAGE_FIXTURES[store.package_heroine]["last"]
        reset_story()
        store.route_id=fixture["route_id"]
        store.relationship_stage=fixture["relationship_stage"]
        store.choice_facts=copy.deepcopy(fixture["choice_facts"])
        store.completed_events=set(fixture["completed_events"])
        store.flow_index=ROUTE_SCHEDULES[store.route_id].index(fixture["chapter"])
        label=renpy.game.script.lookup("route_flow")
        loop=next(node for node in label.block if isinstance(node,renpy.ast.While))
        renpy.jump(loop.name)

label author_package_last:
    $ package_enter_last_chapter()
    return

label author_package_entry:
    $ reset_story()
    $ choice_facts["g_package_probe"] = package_heroine
    jump route_choice

testsuite package_smoke:
    before testcase:
        if not screen "main_menu":
            run MainMenu(confirm=False)
        $ preferences.text_cps=0
        $ preferences.afm_enable=False
        $ _test.timeout=400.0
        $ _test.transition_timeout=.05
    teardown:
        exit
    testcase first_play_and_save:
        parameter heroine = ["haruka","chinatsu","rin","akari"]
        assert eval not persistent.completed_routes
        run SetVariable("package_heroine",heroine)
        run Start("author_package_entry")
        pause .01 until screen "choice"
        assert eval route_id is None
        assert eval len(renpy.get_screen("choice").scope["items"])==4
        click text (PACKAGE_CAPTIONS[heroine])
        pause .01 until eval package_visible_first(heroine)
        assert eval package_rpa_visible(heroine)
        pause .4
        assert eval FileLoadable(PACKAGE_PREFIXES[heroine]+"01",page="chapter")
        run FileSave("entry-"+heroine,page="package",confirm=False)
        assert eval FileLoadable("entry-"+heroine,page="package")
        run SetVariable("choice_facts",{"package_changed":True})
        run SetVariable("route_id",("haruka" if heroine!="haruka" else "chinatsu"))
        run SetVariable("relationship_stage","acquaintance")
        run FileLoad("entry-"+heroine,page="package",confirm=False)
        pause .01 until eval package_visible_first(heroine)
        assert eval route_id==heroine and current_chapter==PACKAGE_PREFIXES[heroine]+"01" and current_scene==PACKAGE_FIXTURES[heroine]["first"]["scene"]
        assert eval relationship_stage=="interest" and choice_facts.get("g_package_probe")==heroine and "package_changed" not in choice_facts
        assert eval package_rpa_visible(heroine)
        screenshot f"package-entry-{heroine}.png"
        $ package_record("entry-save-load",heroine)
        run MainMenu(confirm=False)
    testcase last_chapter_and_reselect:
        parameter heroine = ["haruka","chinatsu","rin","akari"]
        run SetVariable("package_heroine",heroine)
        run Start("author_package_last")
        pause .01 until eval current_chapter==PACKAGE_PREFIXES[heroine]+"10" and renpy.get_screen("say")
        assert eval route_id==heroine and relationship_stage=="dating"
        assert eval FileLoadable(PACKAGE_PREFIXES[heroine]+"10",page="chapter")
        advance until screen "game_ending"
        assert eval heroine in persistent.completed_routes
        assert eval set(ROUTE_SCHEDULES[heroine]).issubset(completed_events)
        assert eval renpy.loadable(CGS[PACKAGE_PREFIXES[heroine]+"_event06"])
        screenshot f"package-ending-{heroine}.png"
        run FileSave("end-"+heroine,page="package",confirm=False)
        run SetVariable("relationship_stage","acquaintance")
        run FileLoad("end-"+heroine,page="package",confirm=False)
        pause .01 until screen "game_ending"
        assert eval route_id==heroine and relationship_stage=="dating"
        click "重选另一条路线"
        pause .01 until screen "choice"
        assert eval route_id is None and relationship_stage=="interest"
        assert eval completed_events=={key for key in PACKAGE_FIXTURES[heroine]["last"]["completed_events"] if key.startswith("g")}
        assert eval not any(key.startswith(("h_","c_","r_","a_")) for key in choice_facts)
        assert eval len(renpy.get_screen("choice").scope["items"])==4
        $ package_record("last-chapter-ending-reselect",heroine)
        run MainMenu(confirm=False)
