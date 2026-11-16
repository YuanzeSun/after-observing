define config.name = "观测结束以后"
define config.version = "1.1"
define config.screen_width = 1920
define config.screen_height = 1080
define config.save_directory = "after-observing-1-1"
define config.window_title = "观测结束以后 · " + config.version
define config.developer = False
define config.history_length = 3000
define config.image_cache_size = 12
define config.rollback_enabled = True
define config.autosave_on_choice = True
define config.has_autosave = True
define config.game_menu_action = ShowMenu("save")
define config.default_music_volume = 0.65
define config.default_sfx_volume = 0.55
define config.main_menu_music = "audio/release/theme.ogg"
define config.main_menu_stop_channels = ["sound","voice","ambient","music"]
default preferences.text_cps = 38
default preferences.afm_time = 12
default persistent.dialogue_size = 34
default persistent.seen_scenes = set()
default persistent.seen_cgs = set()
default persistent.seen_photos = set()
default persistent.heard_music = set()
default persistent.completed_routes = set()
default persistent.completed_chapters = set()
default persistent.chapter_contexts = {}
default route_id = None
default relationship_stage = "acquaintance"
default choice_facts = {}
default completed_events = set()
default current_chapter = ""
default current_scene = ""
default scene_name = ""
default current_date = ""
default actor_states = {}
default current_cg = None
default phone_speaker = None
default active_speaker = None
default speaking_npc = None
default active_photo = None
default current_music = None
default chapter_backup_pending = False
default flow_index = 0
default next_chapter = None

define y = Character("高桥悠介", who_color="#51677c")
define h = Character("藤野遥", who_color="#487286")
define c = Character("小原千夏", who_color="#996940")
define r = Character("佐伯凛", who_color="#58785d")
define a = Character("朝仓灯里", who_color="#656b8d")
define o = Character("冈本航", who_color="#786e60")
define m = Character("森田", who_color="#687b80")
define d = Character("大野", who_color="#6d7c6e")
define z = Character("野崎", who_color="#7c7464")
define t = Character("田边老师", who_color="#72706a")
define n = Character("中村", who_color="#687b80")
define p = Character("水野", who_color="#787164")
define pc = Character("摄影课老师", who_color="#6f7581")

init -20 python:
    import json, os, copy
    from collections import namedtuple
    SceneSpec = namedtuple("SceneSpec", "id title background date period actors music weather camera phone")
    RouteSpec = namedtuple("RouteSpec", "id name prefix chapters color")
    ROUTES = [RouteSpec("haruka","藤野遥","h",tuple("h%02d"%i for i in range(1,11)),"#90bdbf"),RouteSpec("chinatsu","小原千夏","c",tuple("c%02d"%i for i in range(1,11)),"#d4ac78"),RouteSpec("rin","佐伯凛","r",tuple("r%02d"%i for i in range(1,11)),"#a6c18d"),RouteSpec("akari","朝仓灯里","a",tuple("a%02d"%i for i in range(1,11)),"#acb5da")]
    ROUTE_BY_ID = {x.id:x for x in ROUTES}
    ROUTE_SCHEDULES = {route.id:tuple(item for i,key in enumerate(route.chapters,1) for item in ((key,)+({2:("s01","s02"),6:("s03",),8:("s04",)}.get(i,())))) for route in ROUTES}
    CHARACTER_NAMES = {"h":"藤野遥","c":"小原千夏","r":"佐伯凛","a":"朝仓灯里"}
    SCENES = {}
    CHAPTERS = {}
    try:
        CHAPTERS = json.load(renpy.file("data/chapters.json"))
    except IOError:
        pass
    ASSETS = json.load(renpy.file("data/assets.json"))
    SPRITES = {x["key"]:x for x in ASSETS["sprites"] if x["kind"] == "sprite"}
    BACKGROUNDS = ASSETS["backgrounds"]
    CGS = ASSETS["cgs"]
    CG_ORDER = sorted(CGS,key=lambda key:({"s":0,"h":1,"c":2,"r":3,"a":4}.get(key[0],5),key))
    CG_TITLES = json.load(renpy.file("data/cg_titles.json"))
    MUSIC_TITLES = {row["key"]:row["title"] for row in json.load(renpy.file("data/music.json"))}
    PHOTO_KEYS = ["01_bus_bag","02_shop_shutter","03_school_rain","04_platform_green","05_lodge_waiting","06_ticket_window","07_laundry_light","08_bicycle_return","09_shop_box","10_closed_stall","11_last_bus","12_door_lamp"]
    PHOTO_TITLES = dict(zip(PHOTO_KEYS,["公交站的旧袋子","半开的卷帘门","雨后的校门","站台的绿灯","等云的窗边","售票窗","洗衣店的倒影","回来的单车","门里的箱子","收好的小摊","回家的那班车","关门后的一盏灯"]))
    MUSIC = {k:"audio/release/"+k+".ogg" for k in ("theme","club","daily","night","quiet","tender","ending","haruka","chinatsu","rin","akari","playful","waiting","rain","distance","resolve","warm")}
    MUSIC["night"] = MUSIC["theme"]
    AUTHOR = os.environ.get("AFTER_OBSERVING_AUTHOR") == "1" and not renpy.loadable("_release_build")
    config.developer = AUTHOR
    renpy.music.register_channel("ambient",mixer="ambient",loop=True)
    preferences.volumes.setdefault("ambient",0.5)
    preferences.mute.setdefault("ambient",False)
    try:
        SCENE_CATALOG = json.load(renpy.file("data/scenes.json"))
    except IOError:
        SCENE_CATALOG = {}
    for key,path in BACKGROUNDS.items():
        renpy.image("bg "+key,Transform(path,xysize=(1920,1080),fit="cover"))
    for key,path in CGS.items():
        display = Transform(path,xysize=(1920,1080),fit="cover")
        if key == "c_event05":
            # The twelve photographs are actual story props, hung in two rows.
            # Keeping them separate preserves the content and the exact count.
            pieces = [(0,0),display]
            for i,photo_key in enumerate(PHOTO_KEYS):
                x = 790+(i%6)*176
                y = 325+(i//6)*255
                pieces += [(x,y),Solid("#302d2b",xysize=(164,170)),
                           (x+4,y+4),Solid("#f5f0e6",xysize=(156,162)),
                           (x+10,y+17),Transform("images/release/photo_"+photo_key+".png",xysize=(144,128),fit="contain")]
            display = Composite((1920,1080),*pieces)
        renpy.image("cg "+key,display)

init python:
    def reset_story():
        store.route_id = None
        store.relationship_stage = "acquaintance"
        store.choice_facts = {}
        store.completed_events = set()
        store.current_chapter = ""
        store.current_scene = ""
        store.actor_states = {}
        store.current_cg = None
        store.phone_speaker = None
        store.active_speaker = None
        store.speaking_npc = None
        store.active_photo = None
        store.flow_index = 0
        store.next_chapter = None
        renpy.hide_screen("story_photo")
        renpy.hide_screen("lunar_reference")
        renpy.hide_screen("eyepiece_impression")
        renpy.hide_screen("eclipse_reference")

    def chapter(key):
        store.current_chapter = key
        store.chapter_backup_pending = not _in_replay
        memory = key+(":"+store.route_id if key.startswith("s") and store.route_id else "")
        if not _in_replay and memory not in persistent.chapter_contexts:
            persistent.chapter_contexts[memory] = {"route_id":store.route_id,"relationship_stage":store.relationship_stage,"choice_facts":dict(store.choice_facts),"completed_events":set(store.completed_events)}

    def chapter_finished(key):
        if _in_replay:
            renpy.end_replay()
        store.completed_events.add(key)
        memory = key+(":"+store.route_id if key.startswith("s") and store.route_id else "")
        persistent.completed_chapters.add(memory)

    def reset_route_progress():
        store.route_id = None
        store.relationship_stage = "interest"
        store.choice_facts = {key:value for key,value in store.choice_facts.items() if key.startswith("g") or key in ("double_star","joined","moon","outreach")}
        store.completed_events = {key for key in store.completed_events if key.startswith("g")}
        store.current_cg = None
        store.active_photo = None
        store.phone_speaker = None

    def sprite_key(who,state):
        outfit,emotion,pose,camera = state
        return "%s_%s_p%s_%s%s" % (who,outfit,pose[-1],emotion,"_free" if who=="c" and not camera else "")

    def portrait(who):
        state = store.actor_states.get(who,("uniform","normal","pose1",True))
        return portrait_for_state(who,state)

    def portrait_for_state(who,state):
        key = sprite_key(who,state)
        spec = SPRITES[key]
        master = SPRITES[spec["master"]]
        image = Transform(spec["path"],xysize=(1024,1536))
        if spec["path"] != master["path"]:
            image = AlphaMask(image,Transform(master["path"],xysize=(1024,1536)))
        return Transform(image,xysize=(680,1020),fit="contain")

    def render_cast():
        for who in CHARACTER_NAMES:
            renpy.hide("actor_"+who)
        if store.current_cg:
            return
        cast = [who for who in store.actor_states if who!=store.phone_speaker]
        positions = {1:[.5],2:[.28,.75],3:[.16,.5,.84],4:[.08,.36,.64,.92]}.get(len(cast),[])
        for who,pos in zip(cast,positions):
            scale = .88 if len(cast)>2 else 1.0
            tint = BrightnessMatrix(-.12) if store.active_speaker and store.active_speaker != who else IdentityMatrix()
            renpy.show("actor_"+who,what=portrait(who),at_list=[Transform(xalign=pos,yalign=1.0,zoom=scale,matrixcolor=tint)])

    def enter_scene(key,title,bg,date,period,actors,music=None,weather="clear",camera=True,phone=None):
        assert bg in BACKGROUNDS, "Unknown background: "+bg
        assert period in ("day","evening","night"), period
        spec = SceneSpec(key,title,bg,date,period,tuple(actors),music,weather,camera,phone)
        if key in SCENES:
            assert SCENES[key] == spec, "Scene id reused with different metadata: "+key
        SCENES[key] = spec
        store.current_scene = key
        store.scene_name = title
        store.save_name = title
        store.current_date = date
        store.current_cg = None
        store.phone_speaker = phone
        store.active_speaker = None
        store.speaking_npc = None
        store.active_photo = None
        renpy.hide_screen("story_photo")
        renpy.hide_screen("lunar_reference")
        renpy.hide_screen("eyepiece_impression")
        renpy.hide_screen("eclipse_reference")
        store.actor_states = {row[0]:(row[1],row[2],row[3] if len(row)>3 else "pose1",camera) for row in actors}
        renpy.scene()
        visible_background = ASSETS.get("variants",{}).get(bg,{}).get(period,bg)
        renpy.show("bg "+visible_background)
        render_cast()
        renpy.show_screen("chapter_caption")
        if music:
            assert music in MUSIC,music
            if renpy.loadable(MUSIC[music]):
                renpy.music.play(MUSIC[music],channel="music",fadeout=.7,fadein=1.0,if_changed=True)
                store.current_music = music
                if not _in_replay:persistent.heard_music.add(music)
        ambient = "rain_loop" if weather=="rain" else ("wind_loop" if bg in ("roof","road_day","road_evening","road_autumn","riverside","camp_yard","camp_day","school_gate") else "room_loop")
        renpy.music.play("audio/release/"+ambient+".wav",channel="ambient",loop=True,fadeout=.6,fadein=.8,if_changed=True)
        renpy.with_statement(dissolve)

    def expr(who,emotion,pose=None):
        assert emotion in ("normal","smile","puzzled","displeased","shy","sad")
        assert who in store.actor_states or who == store.phone_speaker, "Expression needs an explicit entrance: "+who+" in "+store.current_scene
        state = store.actor_states.get(who,("uniform","normal","pose1",True))
        states = dict(store.actor_states)
        states[who] = (state[0],emotion,pose or state[2],state[3])
        store.actor_states = states
        render_cast()

    def show_actor(who,outfit="uniform",emotion="normal",pose="pose1",camera=True):
        assert who in CHARACTER_NAMES
        states = dict(store.actor_states)
        states[who] = (outfit,emotion,pose,camera)
        store.actor_states = states
        render_cast()
        renpy.with_statement(dissolve)

    def hide_actor(who):
        states = dict(store.actor_states)
        states.pop(who,None)
        store.actor_states = states
        render_cast()

    def carry_camera(carried):
        if "c" in store.actor_states:
            state = store.actor_states["c"]
            states = dict(store.actor_states)
            states["c"] = (state[0],state[1],state[2],bool(carried))
            store.actor_states = states
            render_cast()

    def cg(key):
        assert key in CGS,key
        store.active_photo = None
        for screen_name in ("story_photo","lunar_reference","eyepiece_impression","eclipse_reference"):
            renpy.hide_screen(screen_name)
        store.current_cg = key
        for who in CHARACTER_NAMES:renpy.hide("actor_"+who)
        renpy.show("cg "+key)
        renpy.with_statement(dissolve)

    def end_cg():
        renpy.hide("cg")
        store.active_photo = None
        for screen_name in ("story_photo","lunar_reference","eyepiece_impression","eclipse_reference"):
            renpy.hide_screen(screen_name)
        store.current_cg = None
        render_cast()
        renpy.with_statement(dissolve)

    def photo(key):
        store.active_photo = key
        if not _in_replay and key in PHOTO_KEYS:persistent.seen_photos.add(key)
        renpy.show_screen("story_photo",key=key)
    def close_photo():
        store.active_photo = None
        renpy.hide_screen("story_photo")

    def lunar_reference():
        renpy.show_screen("lunar_reference")
    def eclipse_reference():
        renpy.show_screen("eclipse_reference")

    def mark_read(event,**kwargs):
        if event=="begin":
            node = renpy.game.script.namemap.get(renpy.game.context().current)
            who = getattr(node,"who",None)
            store.speaking_npc = ASSETS.get("npc_portraits",{}).get(who)
            speaker = who if who in CHARACTER_NAMES else None
            if speaker != store.active_speaker:
                store.active_speaker = speaker
                render_cast()
            if not _in_replay:
                if store.current_scene:persistent.seen_scenes.add(store.current_scene)
                if store.current_cg:persistent.seen_cgs.add(store.current_cg)
                store.save_name = store.scene_name
    config.all_character_callbacks.append(mark_read)

    def backup_chapter():
        if store.chapter_backup_pending and store.current_scene and not _in_replay and renpy.get_screen("say") is not None:
            slot = store.current_chapter+("-"+store.route_id if store.current_chapter.startswith("s") and store.route_id else "")
            action = FileSave(slot,page="chapter",confirm=False)
            if action.get_sensitive():
                store.chapter_backup_pending = False
                action()
    config.interact_callbacks.append(backup_chapter)

    def replay_scope(key):
        state = copy.deepcopy(persistent.chapter_contexts.get(key,{}))
        state.update(current_chapter="",current_scene="",actor_states={},current_cg=None,phone_speaker=None,active_speaker=None,active_photo=None,chapter_backup_pending=False)
        return state

    def replay_entries():
        entries = []
        for key,info in CHAPTERS.items():
            if key.startswith("g"):
                entries.append((key,"共通篇 / "+(info["title"] if key in persistent.completed_chapters else "尚未读到"),key))
        for route in ROUTES:
            for key in ROUTE_SCHEDULES[route.id]:
                memory=key+":"+route.id if key.startswith("s") else key
                if key.startswith("s") and memory not in persistent.completed_chapters:
                    continue
                title=CHAPTERS[key]["title"] if memory in persistent.completed_chapters else "尚未读到"
                entries.append((key,route.name+" / "+title,memory))
        return entries

    def route_name():
        return ROUTE_BY_ID[store.route_id].name if store.route_id else "共通篇"

    def slot_label_key(slot):
        return str(FileCurrentPage())+":"+str(slot)

init python:
    build.name = "AfterObserving-"+config.version
    build.directory_name = build.name
    for pattern in ("**/saves/**","**/tests.rpy","**/*_tests.rpy","**/*_tests.rpyc","**/author_*.rpy","**/author_*.rpyc","**/log.txt","**/errors.txt","**/traceback.txt","tools/**","docs/**"):
        build.classify(pattern,None)
    build.archive("assets","all")
    build.classify("game/images/**","assets")
    build.classify("game/audio/**","assets")

init 20 python:
    layout.ARE_YOU_SURE = "确定继续吗？"
    layout.DELETE_SAVE = "要删除这个存档吗？"
    layout.OVERWRITE_SAVE = "要用当前进度覆盖这个存档吗？"
    layout.LOADING = "读取后，尚未保存的进度会丢失。\n要读取这个存档吗？"
    layout.QUIT = "要退出游戏吗？"
    layout.MAIN_MENU = "要返回主菜单吗？\n尚未保存的进度会丢失。"
    layout.CONTINUE = "要继续上次的进度吗？"
    layout.END_REPLAY = "要结束回放吗？"
    layout.SLOW_SKIP = "要开始快进吗？"
    layout.FAST_SKIP_SEEN = "要快进到下一个选项吗？"
    layout.FAST_SKIP_UNSEEN = "要跳过尚未阅读的对白，前往下一个选项吗？"
