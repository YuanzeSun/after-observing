init python:
    _test.timeout = 400.0
    _test.transition_timeout = .05
    _test.screenshot_directory = os.environ.get("AO_SCREENSHOT_DIR",config.basedir+"/.build/qa/screens")
testsuite global:
    teardown:
        exit
testsuite shell:
    testcase menu:
        assert screen "main_menu"
        screenshot "main-menu.png"
        click "操作帮助"
        assert screen "help"
        click "返回"
        click "阅读设置"
        assert screen "preferences"
        click "38"
        assert eval persistent.dialogue_size == 38
        click "返回"
    testcase opening:
        $ preferences.text_cps = 0
        run Start("start")
        advance until screen "choice"
        assert eval current_chapter == "g01"
        assert eval FileLoadable("g01",page="chapter")
        click "先把灰盒的扣件再检查一遍。"
        advance until screen "choice"
        assert eval choice_facts["g01_carry"] == "case"
        screenshot "opening-four-actors.png"
        run MainMenu(confirm=False)
