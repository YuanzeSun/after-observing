# Native script text capture only. This file is excluded from every player build.
# It does not interpret .rpy or synthesize story text.
init python:
    PLAYTHROUGH_ACTIVE = AUTHOR and os.environ.get("AFTER_OBSERVING_CAPTURE") == "1"

init python in native_capture:
    import ast
    import json
    import os
    import sys
    import time
    import types

    def state():
        return sys.modules.setdefault("_after_observing_native_capture_v11",types.SimpleNamespace())

    def safe(value):
        if isinstance(value,dict):return {str(k):safe(v) for k,v in value.items()}
        if isinstance(value,(set,frozenset)):return sorted(safe(v) for v in value)
        if isinstance(value,(list,tuple)):return [safe(v) for v in value]
        if value is None or isinstance(value,(str,int,float,bool)):return value
        return str(value)

    def source_name(filename):
        filename=str(filename).replace("\\","/")
        if "/game/" in filename:return "game/"+filename.split("/game/",1)[1]
        if filename.startswith("game/"):return filename
        if filename.startswith("story/"):return "game/"+filename
        return filename

    def location():
        node=renpy.game.script.namemap.get(renpy.game.context().current)
        filename,line=renpy.get_filename_line()
        filename=source_name(getattr(node,"filename",filename))
        line=getattr(node,"linenumber",line)
        return node,filename,int(line or 0)

    def facts():
        return {"route_id":renpy.store.route_id,"chapter":renpy.store.current_chapter,"scene":renpy.store.current_scene,"scene_title":renpy.store.scene_name,"date":renpy.store.current_date,"choice_facts":safe(renpy.store.choice_facts),"relationship_stage":renpy.store.relationship_stage,"completed_events":sorted(renpy.store.completed_events)}

    def emit(kind,**fields):
        s=state()
        if not getattr(s,"handle",None):return
        s.seq+=1
        row={"kind":kind,"seq":s.seq,"path_id":s.settings["path_id"],"target_route":s.settings["route_id"],**facts(),**fields}
        s.handle.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")

    def begin():
        s=state()
        with open(os.environ["AFTER_OBSERVING_CAPTURE_CASE"],encoding="utf8") as f:s.settings=json.load(f)
        s.seq=0;s.says=0;s.choices=0;s.stop_reached=False;s.scenes=[]
        s.directory=s.settings["directory"]
        s.handle=open(os.path.join(s.directory,"events.jsonl"),"w",encoding="utf8",buffering=1)
        emit("run_start",source_fingerprint=s.settings["source_fingerprint"],runtime_fingerprint=s.settings["runtime_fingerprint"],native_script=True,text_only=True,entry_label="start",variant=s.settings["variant"])

    def prepare_text_only():
        # Run the ORIGINAL scene/expr/CG helpers and their semantic assertions.
        # Suppress only media presentation in this disposable development process.
        # No player source or persistent progress is used by this process.
        renpy.config.save=False
        renpy.game.preferences.text_cps=0
        renpy.game.preferences.afm_enable=False
        # Fast skipping returns before Character callbacks in this SDK. Use
        # native Advance throughout so every executed Say reaches the recorder.
        renpy.config.skipping=None
        renpy.config.fast_skipping=False
        visual_screens={"chapter_caption","notebook","story_photo","lunar_reference","eyepiece_impression","eclipse_reference"}
        original_show_screen=renpy.show_screen
        original_hide_screen=renpy.hide_screen
        def show_screen(name,*args,**kwargs):
            key=name[0] if isinstance(name,(tuple,list)) else name
            if key in visual_screens:return
            return original_show_screen(name,*args,**kwargs)
        def hide_screen(name,*args,**kwargs):
            key=name[0] if isinstance(name,(tuple,list)) else name
            if key in visual_screens:return
            return original_hide_screen(name,*args,**kwargs)
        def no_media(*args,**kwargs):return None
        for module in (renpy,renpy.exports):
            module.show=no_media
            module.hide=no_media
            module.scene=no_media
            module.with_statement=no_media
            module.show_screen=show_screen
            module.hide_screen=hide_screen
        renpy.music.play=no_media
        renpy.music.stop=no_media

    def say(event,what=None,**kwargs):
        s=state()
        if event!="begin" or not getattr(s,"handle",None):return
        stop=s.settings.get("stop_after")
        if stop and stop in renpy.store.completed_events:
            s.stop_reached=True
            return
        node,source,line=location()
        if not isinstance(node,renpy.ast.Say) or not source.startswith("game/story/"):return
        who=getattr(node,"who",None)
        speaker=""
        if who:
            try:
                if who.startswith(("\"","'")):speaker=ast.literal_eval(who)
                else:speaker=getattr(renpy.store,who).name
                if callable(speaker):speaker=speaker()
                speaker=renpy.substitute(str(speaker))
            except Exception:speaker=str(who)
        text=what if what is not None else getattr(node,"what","")
        text=renpy.substitute(str(text))
        s.says+=1
        if not s.scenes or s.scenes[-1]!=renpy.store.current_scene:s.scenes.append(renpy.store.current_scene)
        emit("say",node_id=source+":"+str(line)+":"+repr(node.name),ast_name=safe(node.name),speaker=speaker,text=text,source_text=getattr(node,"what",None),source=source,line=line)

    def done():
        return bool(renpy.get_screen("game_ending")) or state().stop_reached

    def boundary():
        return bool(renpy.get_screen("choice")) or done()

    def next_caption():
        s=state();screen=renpy.get_screen("choice")
        assert screen is not None,"No native choice screen"
        items=[item for item in screen.scope["items"] if item.action is not None]
        assert items,"Native choice has no selectable entries"
        node,source,line=location();menu_id=source+":"+str(line)
        is_route=source=="game/flow.rpy" and renpy.store.current_chapter=="g06"
        if is_route:
            index=[route.id for route in renpy.store.ROUTES].index(s.settings["route_id"])
        else:
            override=s.settings.get("choices",{})
            index=int(override.get(menu_id,override.get(str(s.choices+1),s.settings["variant"])))
        assert 0<=index<len(items),(menu_id,index,len(items))
        s.choices+=1
        assert s.choices<=s.settings.get("max_menus",150),"Menu cycle or unexpected extra choices"
        emit("choice",node_id=menu_id+":"+repr(getattr(node,"name",None)),menu_id=menu_id,source=source,line=line,options=[str(item.caption) for item in items],selected=index,selected_caption=str(items[index].caption),route_selection=is_route)
        return str(items[index].caption)

    def finish():
        s=state();ending=bool(renpy.get_screen("game_ending"))
        completed=ending and renpy.store.route_id==s.settings["route_id"] and renpy.store.route_id in renpy.store.persistent.completed_routes
        if ending:assert completed,"Native ending did not complete the requested route"
        emit("ending" if completed else "checkpoint",completed=completed,stopped_after=s.settings.get("stop_after"),native_script=True,text_only=True)
        s.handle.close();s.handle=None
        meta={"format_version":1,"path_id":s.settings["path_id"],"route_id":s.settings["route_id"],"variant":s.settings["variant"],"choices":s.settings.get("choices",{}),"events":"events.jsonl","completed":completed,"say_count":s.says,"choice_count":s.choices,"scene_order":s.scenes,"source_fingerprint":s.settings["source_fingerprint"],"runtime_fingerprint":s.settings["runtime_fingerprint"],"native_script":True,"text_only":True,"stop_after":s.settings.get("stop_after")}
        path=os.path.join(s.directory,"run.json")
        with open(path+".tmp","w",encoding="utf8") as f:json.dump(meta,f,ensure_ascii=False,indent=2)
        os.replace(path+".tmp",path)
        print("NATIVE_CAPTURE_COMPLETE",json.dumps(meta,ensure_ascii=False))

init python:
    if PLAYTHROUGH_ACTIVE:
        config.all_character_callbacks.append(native_capture.say)

# Ren'Py image declarations are init-only. These neutral media substitutes exist
# solely in an explicitly enabled disposable TEXT capture process, never a build.
init 100 python:
    if PLAYTHROUGH_ACTIVE:
        for capture_cg_key in CGS:
            renpy.image("cg "+capture_cg_key,Solid("#142437"))

testsuite playthrough:
    testcase native_run:
        enabled PLAYTHROUGH_ACTIVE
        $ _test.timeout = 1800.0
        $ _test.transition_timeout = 0.0
        $ native_capture.begin()
        $ native_capture.prepare_text_only()
        run Start("start")
        while eval not native_capture.done():
            advance until eval native_capture.boundary()
            if screen "choice":
                $ capture_caption = native_capture.next_caption()
                click text capture_caption
                pause .001
        $ native_capture.finish()
    teardown:
        exit
