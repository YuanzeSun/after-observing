# Optional gallery unlock. This file contains no saves or story progress.
init 999 python:
    def _after_observing_unlock_cg_gallery():
        if config.save_directory == "after-observing-1-1":
            persistent.seen_cgs.update(CGS)
            renpy.save_persistent()

    config.start_callbacks.append(_after_observing_unlock_cg_gallery)
