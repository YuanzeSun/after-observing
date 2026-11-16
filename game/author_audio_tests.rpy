# Actual native output checks. Excluded from player builds.
init python:
    import os as author_audio_os
    import json as author_audio_json
    import time as author_audio_clock

    def author_audio_mark(name, kind="segment", duration=None):
        row = {"name": name, "kind": kind,
               "time": author_audio_clock.time(),
               "monotonic": author_audio_clock.monotonic()}
        if duration is not None:
            row["duration"] = duration
        with open(author_audio_os.environ["AO_AUDIO_MARKS"], "a", encoding="utf-8") as f:
            f.write(author_audio_json.dumps(row) + "\n")

    def author_audio_stop():
        for channel in ("music", "ambient", "sound"):
            renpy.music.stop(channel=channel, fadeout=0)

    def author_audio_reset():
        Preference("all mute", "disable")()
        author_audio_stop()

    def author_audio_play(name, channel, filename, duration, kind="segment", stop=False):
        if stop:
            author_audio_stop()
        # Mark and enqueue in one action, without a testcase interaction between them.
        author_audio_mark(name, kind, duration)
        renpy.music.play(filename, channel=channel, fadeout=0, fadein=0,
                         loop=(channel == "music"))

    def author_audio_mixed():
        author_audio_mark("mixed", duration=2.4)
        renpy.music.play(MUSIC["club"], channel="music", fadeout=0, fadein=0)
        renpy.music.play("audio/release/wind_loop.wav", channel="ambient", loop=True)

    def author_audio_mute(enabled):
        # Exercise the same real Preference action as the settings screen.
        Preference("all mute", "enable" if enabled else "disable")()
        author_audio_mark("muted" if enabled else "restored", duration=2.4)

testsuite audio_output:
    testcase calibration:
        run Function(author_audio_reset)
        pause 3.0
        run Function(author_audio_play, "sync-head", "sound", "audio/release/ui_select.wav", 1.2, "calibration")
        pause 1.2
    testcase music:
        parameter track = ["theme","club","daily","quiet","tender","ending","haruka","chinatsu","rin","akari","playful","waiting","rain","distance","resolve","warm"]
        run Function(author_audio_play, track, "music", MUSIC[track], 3.0)
        pause 3.0
    testcase effects:
        parameter effect = ["paper","ui_hover","ui_select"]
        run Function(author_audio_play, "sfx-"+effect, "sound", "audio/release/"+effect+".wav", .8, "segment", True)
        pause .8
    testcase mute:
        run Function(author_audio_stop)
        pause 1.0
        run Function(author_audio_play, "sync-middle", "sound", "audio/release/ui_select.wav", 1.2, "calibration")
        pause 1.2
        run Function(author_audio_mixed)
        pause 2.4
        run Function(author_audio_mute, True)
        assert eval all(preferences.get_mute(mixer) for mixer in ("music","sfx","voice","ambient"))
        pause 2.4
        run Function(author_audio_mute, False)
        assert eval all(not preferences.get_mute(mixer) for mixer in ("music","sfx","voice","ambient"))
        pause 2.4
        run Function(author_audio_stop)
        pause 1.0
        run Function(author_audio_play, "sync-tail", "sound", "audio/release/ui_select.wav", 1.2, "calibration")
        pause 1.2
        run Function(author_audio_mark, "complete", "boundary")
