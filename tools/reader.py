"""Build a self-contained review reader from completed native Ren'Py captures.

No .rpy statements are executed or interpreted here. Story text, selected choices
and preceding state come exclusively from genuine JSONL emitted by Ren'Py.
Missing/stale/incomplete captures fail before replacing any deliverable.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import argparse
import base64
import hashlib
import html
import io
import json
import re
import sys

from playthrough import source_fingerprint, runtime_digest

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT
from paths import WORK, DIST, VERSION
ROUTES = {'haruka': '遥', 'chinatsu': '千夏', 'rin': '凛', 'akari': '灯里'}
PREFIXES = dict(zip(ROUTES, 'hcra'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf8'))
    except (OSError, ValueError) as exc:
        raise ValueError(f'无法读取 {path}: {exc}') from exc


def inside(directory, relative):
    require(isinstance(relative, str) and relative, '缺少数据相对路径')
    path = (directory / relative).resolve()
    require(path.is_relative_to(directory.resolve()), f'数据路径越界: {relative}')
    require(path.is_file(), f'缺少真实导出文件: {path}')
    return path


def expected_order(route):
    result = [f'g{i:02}' for i in range(1, 7)]
    for i in range(1, 11):
        result.append(f'{PREFIXES[route]}{i:02}')
        result.extend({2: ['s01', 's02'], 6: ['s03'], 8: ['s04']}.get(i, []))
    return result


def load_native(directory):
    index = read_json(directory / 'index.json')
    require(index.get('format_version') == 1, '不支持的原生导出版本')
    fingerprint, runtime = source_fingerprint(), runtime_digest()
    require(index.get('source_fingerprint') == fingerprint, '原生导出与当前故事稿指纹不一致；请重新运行原生导出')
    require(index.get('runtime_fingerprint') == runtime, '原生导出与当前运行工程指纹不一致；请重新运行原生导出')
    coverage = index.get('coverage', {})
    require(not coverage.get('source_changed', True), '导出期间故事稿发生变化')
    require(coverage.get('errors') == [], '原生导出仍有错误，拒绝生成全文阅读器')
    require(coverage.get('uncovered_nodes') == 0, '原生运行尚未覆盖全部正文；请补齐真实路径')
    require(set(coverage.get('completed_routes', [])) == set(ROUTES), '四条路线必须全部真实抵达结局')
    chapters = read_json(PROJECT / 'game/data/chapters.json')
    require(len(chapters) == 50, '章节登记必须为50章')
    nodes, node_ids, contexts, context_ids, paths = [], {}, [], {}, []
    observed, scene_data, seen_paths = {}, {}, set()
    for run in index.get('runs', []):
        path_id, route = run.get('path_id'), run.get('route_id')
        require(isinstance(path_id, str) and re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}', path_id), '无效游玩路径标识')
        require(path_id not in seen_paths, f'重复路径: {path_id}')
        seen_paths.add(path_id)
        require(route in ROUTES, f'未知路线: {route}')
        metadata = read_json(inside(directory, run.get('metadata')))
        for name in ('path_id', 'route_id', 'variant', 'completed', 'source_fingerprint', 'runtime_fingerprint', 'say_count', 'choice_count'):
            require(run.get(name) == metadata.get(name), f'{path_id} 索引与run.json不一致: {name}')
        require(metadata.get('format_version') == 1, f'{path_id} run.json版本不受支持')
        require(metadata.get('completed') is True and metadata.get('native_script') is True, f'{path_id} 没有真实结局')
        require(metadata.get('source_fingerprint') == fingerprint and metadata.get('runtime_fingerprint') == runtime, f'{path_id} 指纹过期')
        events_path = inside(directory, run.get('events'))
        events = []
        try:
            for line_number, line in enumerate(events_path.read_text(encoding='utf8').splitlines(), 1):
                require(bool(line.strip()), f'{path_id}:{line_number} 空事件')
                events.append(json.loads(line))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f'损坏的原生事件文件 {events_path}: {exc}') from exc
        require(events and events[0].get('kind') == 'run_start', f'{path_id} 缺少原生起点')
        start, ending = events[0], events[-1]
        require(start.get('native_script') is True and start.get('source_fingerprint') == fingerprint and start.get('runtime_fingerprint') == runtime, f'{path_id} 起点指纹不一致')
        require(ending.get('kind') == 'ending' and ending.get('completed') is True and ending.get('route_id') == route and ending.get('native_script') is True, f'{path_id} 缺少真实 game_ending 结局；checkpoint不能用作全文')
        require(metadata['say_count'] == sum(e.get('kind') == 'say' for e in events), f'{path_id} 对白数量不一致')
        require(metadata['choice_count'] == sum(e.get('kind') == 'choice' for e in events), f'{path_id} 选择数量不一致')
        compact, order, last_chapter, menus, seq = [], [], None, set(), 0
        for event in events:
            require(isinstance(event.get('seq'), int) and event['seq'] == seq + 1, f'{path_id} 事件序号不连续')
            seq = event['seq']
            require(event.get('path_id') == path_id and event.get('target_route') == route, f'{path_id} 混入其他路径事件')
            kind = event.get('kind')
            require(kind in ('run_start', 'say', 'choice', 'ending'), f'{path_id} 出现未完成/未知事件: {kind}')
            if kind not in ('say', 'choice'):
                continue
            chapter = event.get('chapter')
            require(chapter in chapters, f'{path_id} 未登记章节: {chapter}')
            if chapter != last_chapter:
                order.append(chapter)
                last_chapter = chapter
            source, source_line = event.get('source'), event.get('line')
            require(isinstance(source, str) and source.startswith('game/') and '..' not in Path(source).parts, f'{path_id} 无效源码位置')
            require(isinstance(source_line, int) and source_line > 0, f'{path_id} 缺少源码行号')
            node = event.get('node_id')
            require(isinstance(node, str) and node, f'{path_id} 缺少真实AST节点')
            if node not in node_ids:
                node_ids[node] = len(nodes)
                nodes.append([source, source_line, chapter, node])
            else:
                require(nodes[node_ids[node]][:3] == [source, source_line, chapter], f'{path_id} AST节点位置冲突')
            scene = event.get('scene')
            require(isinstance(scene, str) and scene, f'{path_id} 缺少实际场景')
            scene_info = [event.get('scene_title'), event.get('date'), chapter]
            if scene in scene_data:
                require(scene_data[scene] == scene_info, f'场景元数据冲突: {scene}')
            else:
                scene_data[scene] = scene_info
            facts, completed = event.get('choice_facts'), event.get('completed_events')
            require(isinstance(facts, dict) and isinstance(completed, list), f'{path_id} 缺少真实前情')
            context = {'chapter': chapter, 'scene': scene, 'title': scene_info[0], 'date': scene_info[1], 'route': event.get('route_id'), 'stage': event.get('relationship_stage'), 'facts': facts, 'completed': completed}
            context_key = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            if context_key not in context_ids:
                context_ids[context_key] = len(contexts)
                contexts.append(context)
            item = {'k': 's' if kind == 'say' else 'c', 'n': node_ids[node], 'c': context_ids[context_key], 'q': seq}
            if kind == 'say':
                text, speaker = event.get('text'), event.get('speaker')
                require(isinstance(text, str) and isinstance(speaker, str), f'{path_id} 对白不是原生文本')
                require(source.startswith('game/story/'), f'{path_id} 对白来自正式剧情之外')
                item.update(t=text, s=speaker)
                position = (source, source_line)
                old = observed.get(position)
                if old is None or len(text) > len(old[1]):
                    observed[position] = (chapter, text)
            else:
                options, selected = event.get('options'), event.get('selected')
                require(isinstance(options, list) and options and all(isinstance(x, str) for x in options), f'{path_id} 选择项无效')
                require(isinstance(selected, int) and 0 <= selected < len(options), f'{path_id} 选择越界')
                require(options[selected] == event.get('selected_caption'), f'{path_id} 选择文案不一致')
                menu_id = event.get('menu_id')
                require(menu_id and menu_id not in menus, f'{path_id} 菜单重复，可能导出未推进: {menu_id}')
                menus.add(menu_id)
                item.update(o=options, i=selected, r=bool(event.get('route_selection')))
            compact.append(item)
        require(order == expected_order(route), f'{path_id} 没有按完整20章顺序运行: {order}')
        require(metadata.get('scene_order') == list(dict.fromkeys(contexts[e['c']]['scene'] for e in compact if e['k'] == 's')), f'{path_id} 实际场景目录与run.json不一致')
        require(set(ending.get('completed_events', [])) >= set(order), f'{path_id} 结局未登记全部已完成章节')
        paths.append({'id': path_id, 'route': route, 'variant': run.get('variant'), 'events': compact, 'order': order, 'choices': metadata.get('choices', {}), 'characters': sum(len(x['t']) for x in compact if x['k'] == 's')})
    require(paths and {p['route'] for p in paths} == set(ROUTES), '缺少四条路线的完整原生路径')
    union_chapters = Counter()
    for chapter, text in observed.values():
        union_chapters[chapter] += len(text)
    require(set(union_chapters) == set(chapters), '原生记录没有覆盖全部50章')
    require(len(observed) == index.get('union', {}).get('nodes') == coverage.get('source_nodes'), '实际正文节点并集与原生覆盖索引不一致')
    require(dict(union_chapters) == index.get('union', {}).get('chapters'), '实际章节字数与原生并集不一致')
    require(sum(union_chapters.values()) == index.get('union', {}).get('characters'), '实际字数并集不一致')
    require(source_fingerprint() == fingerprint and runtime_digest() == runtime, '读取导出时工程发生变化；请在冻结后重试')
    return {'format': 1, 'fingerprint': fingerprint, 'runtime': runtime, 'chapters': chapters, 'routes': ROUTES, 'nodes': nodes, 'contexts': contexts, 'scenes': scene_data, 'paths': paths, 'union': index['union']}


TEMPLATE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark">
<meta http-equiv="Content-Security-Policy" content="default-src 'none';script-src 'unsafe-inline';style-src 'unsafe-inline';font-src data:;img-src data:;base-uri 'none';form-action 'none'">
<title>观测结束以后 __VERSION__｜离线全文</title>
<style>
__FONT__
:root{--paper:#f4f3f9;--sheet:#fff;--ink:#292a40;--muted:#65667b;--line:#dcdeeb;--accent:#615487;--soft:#ece8f5;--focus:#147a82;--size:20px;--nav:300px}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:AfterObservingReader,sans-serif;line-height:1.7}body.night{--paper:#1a1d2b;--sheet:#232738;--ink:#e4e6f1;--muted:#acb2ca;--line:#3d425b;--accent:#c6b9ee;--soft:#343147;--focus:#8ed5dc}button,input,select{font:inherit;color:inherit}button,select{cursor:pointer}button{border:1px solid var(--line);background:var(--sheet);padding:.45em .8em;border-radius:6px}button:hover{border-color:var(--accent);background:var(--soft)}button:disabled{cursor:default;opacity:.5}button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid var(--focus);outline-offset:3px}input,select{background:var(--sheet);border:1px solid var(--line);border-radius:5px;padding:.45em .6em;max-width:100%}input[type=checkbox]{accent-color:var(--accent)}a{color:var(--accent)}header{position:sticky;top:0;z-index:10;height:76px;padding:10px 26px;display:flex;align-items:center;gap:14px;background:var(--sheet);border-bottom:1px solid var(--line)}.brand{font-size:20px;line-height:1.35;letter-spacing:.08em}.edition{display:block;letter-spacing:0;color:var(--muted);font-size:12px;margin-top:4px}.header-actions{margin-left:auto;display:flex;gap:9px;font-size:14px}.mobile-menu{display:none}.progress{position:absolute;bottom:0;left:0;height:3px;background:var(--accent);width:0}.layout{display:grid;grid-template-columns:var(--nav) 1fr;max-width:1600px;margin:0 auto}aside{position:sticky;top:76px;height:calc(100vh - 76px);padding:24px 20px;overflow:auto;scrollbar-width:thin;border-right:1px solid var(--line)}.route-tabs{display:grid;grid-template-columns:repeat(4,1fr);gap:5px}.route-tabs button{padding:7px 1px;font-size:15px}.route-tabs button[aria-pressed=true]{color:var(--accent);border-color:var(--accent);background:var(--soft);font-weight:600}.path-label{display:block;font-size:13px;color:var(--muted);margin:18px 0 5px}.path-select{width:100%;font-size:13px}.catalog-button{width:100%;margin:12px 0 8px;font-size:13px;background:transparent}.chapter-list,.scene-list{list-style:none;margin:0;padding:0}.chapter-list li{margin:2px 0}.chapter-list button{text-align:left;border:0;background:transparent;border-radius:4px;display:block;width:100%;padding:8px 9px;line-height:1.45;font-size:14px}.chapter-list button.current{background:var(--soft);color:var(--accent);font-weight:600}.chapter-list small{color:var(--muted);font-size:11px;display:block;font-weight:400;margin-bottom:2px}.scene-directory{font-size:13px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin:8px 0 15px;padding:11px 0}.scene-list a{display:block;padding:6px 4px;text-decoration:none;line-height:1.5}.scene-list a:hover{text-decoration:underline}.nav-note{color:var(--muted);font-size:12px;margin:19px 0 4px}.main-wrap{min-width:0}main{max-width:43em;margin:auto;padding:38px 48px 60px;font-size:var(--size);min-height:80vh}.chapter-heading{margin-bottom:28px;padding-bottom:24px;border-bottom:1px solid var(--line)}.chapter-heading h1{font-size:1.55em;line-height:1.45;font-weight:600;letter-spacing:.04em;margin:7px 0 14px}.chapter-meta{font-size:13px;color:var(--muted);margin:0}.path-context{font-size:13px;color:var(--muted);line-height:1.65;margin:8px 0 12px}.notice{font-size:13px;padding:12px 15px;background:var(--soft);margin:0 0 24px;border-left:3px solid var(--accent)}.scene{scroll-margin-top:100px;margin:34px 0 58px}.scene-head{margin-bottom:25px;display:flex;align-items:flex-start;gap:12px;flex-wrap:wrap}.scene-head h2{font-size:1em;font-weight:600;margin:0;line-height:1.6;flex:1 1 200px}.scene-head time{display:block;color:var(--muted);font-size:12px;font-weight:400;margin-top:3px}.context-button{font-size:12px;white-space:nowrap;background:transparent;padding:4px 9px}.say{margin:0 0 1.05em;scroll-margin-top:105px;border-radius:3px}.say .speaker{display:block;color:var(--accent);font-size:.72em;font-weight:600;margin-bottom:1px;letter-spacing:.05em}.say p{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.95}.say.narration{color:var(--ink)}.say.dialogue{padding-left:14px;border-left:2px solid var(--line)}.source{display:none;font-size:11px;color:var(--muted);overflow-wrap:anywhere;line-height:1.5;margin-top:6px}body.sources .source{display:block}.highlight{background:var(--soft);box-shadow:0 0 0 8px var(--soft)}.choice{margin:30px 0;padding:18px 20px;background:var(--sheet);border:1px solid var(--line);border-radius:7px;font-size:.78em;scroll-margin-top:100px}.choice-title{font-size:12px;color:var(--muted);margin-bottom:9px}.choice ul{padding:0;list-style:none;margin:0}.choice li{padding:7px 0;line-height:1.7}.choice .selected{color:var(--accent);font-weight:600}.choice .selected:before{content:'已选　';font-size:11px;white-space:nowrap}.choice details{margin-top:8px;color:var(--muted);font-size:12px}.alternative{display:block;width:100%;text-align:left;margin-top:9px;line-height:1.65}.chapter-controls{display:flex;gap:12px;justify-content:space-between;border-top:1px solid var(--line);padding-top:24px;font-size:14px}.chapter-controls button{max-width:48%;text-align:left;line-height:1.6}.chapter-controls small{display:block;font-size:11px;color:var(--muted)}footer{color:var(--muted);font-size:12px;padding:0 32px 35px;text-align:center}footer button{font-size:12px;background:transparent}.veil{display:none}dialog{overflow:auto;background:var(--sheet);color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:0;width:min(720px,calc(100% - 32px));max-height:86vh;box-shadow:0 16px 70px #0003}dialog::backdrop{background:#14182b99}.dialog-head{display:flex;align-items:center;justify-content:space-between;gap:15px;padding:18px 22px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--sheet);z-index:1}.dialog-head h2{font-size:19px;margin:0}.dialog-body{padding:22px;overflow-wrap:anywhere}.dialog-close{font-size:13px}.search-fields{display:flex;gap:8px;flex-wrap:wrap}.search-fields input{flex:1 1 240px;min-width:0}.search-fields select{font-size:13px}.result-count{color:var(--muted);font-size:13px}.results{display:grid;gap:12px}.search-result{text-align:left;display:block;width:100%;padding:13px 14px;line-height:1.75}.search-result small{display:block;font-size:11px;color:var(--muted);margin-bottom:7px}.search-result p{margin:0;font-size:15px}.search-result mark{background:var(--soft);color:var(--accent);font-weight:600}.settings-row{display:flex;gap:12px;align-items:center;justify-content:space-between;margin:0 0 24px}.settings-row label{display:flex;gap:8px;align-items:center}.settings-row input[type=range]{width:160px;padding:0}.muted{color:var(--muted);font-size:13px}.context-choices{list-style:none;padding:0;font-size:14px}.context-choices li{padding:9px 0;border-bottom:1px solid var(--line)}.context-choices small{display:block;color:var(--muted);font-size:11px}.state-data{font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere}.catalog-group{margin:0 0 26px}.catalog-group h3{font-size:16px;margin:0 0 10px}.catalog-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px}.catalog-grid button{text-align:left;font-size:13px;line-height:1.55}.license{white-space:pre-wrap;font-size:12px;line-height:1.65}.empty{padding:28px 0;color:var(--muted)}#searchMore{margin-top:16px}noscript{display:block;padding:30px}
@media(min-width:1450px){:root{--nav:330px}main{padding-left:65px;padding-right:65px}}
@media(max-width:760px){header{height:68px;padding:9px 13px;gap:10px}.brand{font-size:15px;letter-spacing:.03em}.edition{font-size:10px;margin-top:2px}.header-actions{gap:6px;font-size:12px}.header-actions button{padding:7px 9px}.mobile-menu{display:block;font-size:12px;padding:7px 9px}.layout{display:block}aside{display:none;position:fixed;left:0;top:68px;width:min(320px,88vw);height:calc(100dvh - 68px);z-index:20;background:var(--paper);padding:22px 18px;box-shadow:10px 0 30px #0002}body.nav-open aside{display:block}body.nav-open .veil{display:block;position:fixed;inset:68px 0 0;background:#10162a77;z-index:19}.chapter-heading h1{font-size:1.35em}main{padding:28px 23px 45px;font-size:var(--size)}.scene{margin:30px 0 45px}.scene-head{margin-bottom:22px}.scene-head h2{flex-basis:190px}.choice{padding:15px 16px}.dialogue{padding-left:11px!important}.dialog-head,.dialog-body{padding:17px}.dialog-head h2{font-size:17px}.catalog-grid{grid-template-columns:1fr}.chapter-controls{gap:8px;font-size:12px}footer{padding:0 23px 25px}.settings-row{font-size:14px}.settings-row input[type=range]{width:130px}dialog{max-height:88dvh}.source{font-size:10px}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
@media print{header,aside,footer,.chapter-controls,.context-button,.choice details{display:none!important}.layout{display:block}main{max-width:none;padding:0;font-size:12pt}body{background:white;color:black}.scene{break-inside:auto}.choice{break-inside:avoid}.source{display:none!important}}
</style></head><body>
<header><button class="mobile-menu" id="menuButton" aria-expanded="false" aria-controls="sidebar">目录</button><div class="brand">观测结束以后<span class="edition">__VERSION__ 离线全文 / 审稿阅读版</span></div><div class="header-actions"><button id="searchButton">搜索</button><button id="settingsButton">阅读设置</button></div><div class="progress" id="progress"></div></header>
<div class="veil" id="veil"></div><div class="layout"><aside id="sidebar" aria-label="路线与章节"><div class="route-tabs" id="routeTabs"></div><label class="path-label" for="pathSelect">本次阅读的完整选法</label><select class="path-select" id="pathSelect"></select><button class="catalog-button" id="catalogButton">查看全部 50 章</button><details class="scene-directory"><summary id="sceneSummary">本章场景</summary><ul class="scene-list" id="sceneList"></ul></details><nav aria-label="当前路径章节"><ol class="chapter-list" id="chapterList"></ol></nav><p class="nav-note">共享篇随当前路线保留前情。每种选法均来自一条真实抵达结局的游玩记录。</p></aside><div class="main-wrap"><main id="reading" tabindex="-1"><p>正在打开全文……</p></main><footer><p id="evidence"></p><button id="creditsButton">字体授权与阅读说明</button></footer></div></div>
<dialog id="searchDialog" aria-labelledby="searchTitle"><div class="dialog-head"><h2 id="searchTitle">搜索全文</h2><button class="dialog-close" data-close>关闭</button></div><div class="dialog-body"><div class="search-fields"><input id="searchInput" type="search" placeholder="台词、人物名或一句话" aria-label="搜索关键词"><select id="searchScope" aria-label="搜索范围"><option value="all">全部四线</option><option value="route">当前路线</option><option value="path">当前选法</option></select></div><p class="result-count" id="resultCount">输入关键词即可搜索，选择文字也可搜索。</p><div class="results" id="searchResults"></div><button id="searchMore" hidden>再显示 100 条</button></div></dialog>
<dialog id="settingsDialog" aria-labelledby="settingsTitle"><div class="dialog-head"><h2 id="settingsTitle">阅读设置</h2><button class="dialog-close" data-close>关闭</button></div><div class="dialog-body"><div class="settings-row"><label for="fontSize">字号 <output id="fontOutput"></output></label><input id="fontSize" type="range" min="16" max="28" step="1"></div><div class="settings-row"><label><input id="nightToggle" type="checkbox">夜间阅读</label></div><div class="settings-row"><label><input id="sourceToggle" type="checkbox">显示源码位置</label></div><p class="muted">进度和设置仅保存在当前浏览器。本文件包含全部文字和字体，打开后不需要联网。</p></div></dialog>
<dialog id="contextDialog" aria-labelledby="contextTitle"><div class="dialog-head"><h2 id="contextTitle">到这里的前情</h2><button class="dialog-close" data-close>关闭</button></div><div class="dialog-body" id="contextBody"></div></dialog>
<dialog id="catalogDialog" aria-labelledby="catalogTitle"><div class="dialog-head"><h2 id="catalogTitle">全部 50 章</h2><button class="dialog-close" data-close>关闭</button></div><div class="dialog-body"><p class="muted" id="catalogContext"></p><div id="catalogBody"></div></div></dialog>
<dialog id="creditsDialog" aria-labelledby="creditsTitle"><div class="dialog-head"><h2 id="creditsTitle">字体授权与阅读说明</h2><button class="dialog-close" data-close>关闭</button></div><div class="dialog-body"><p>本文件保留完整游玩路径。选择另一选法时会转到另一条真实游玩记录，之前的选择也可能不同；可用“到这里的前情”核对。</p><p>文字来自 Ren’Py 原生运行，未用静态脚本解释器拼接剧情。正文节点按源码位置去重统计，互斥分支均在收录路径中可查。</p><p id="fingerprints" class="state-data"></p><p>内嵌字体基于 Noto Sans CJK SC，© 2014–2021 Adobe，采用 SIL Open Font License 1.1；本文件子集字体已更名为 After Observing Reader。</p><pre class="license">__LICENSE__</pre></div></dialog>
<noscript>请在支持 JavaScript 的浏览器中打开此离线文件。无需联网。</noscript>
<script type="application/json" id="nativeData">__DATA__</script>
<script>
'use strict';
const D=JSON.parse(document.getElementById('nativeData').textContent),$=id=>document.getElementById(id),key='after-observing-reader-'+D.fingerprint;
const make=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e};
const readSaved=k=>{try{return JSON.parse(localStorage.getItem(k)||'null')}catch{return null}},saved=readSaved(key)||{},prefs=readSaved('after-observing-reader-settings')||{};
let state={path:Math.max(0,D.paths.findIndex(p=>p.id===saved.path)),chapter:saved.chapter||'g01'},searchMatches=[],searchShown=0,searchTimer=null,saveTimer=null;
const ctx=e=>D.contexts[e.c],path=()=>D.paths[state.path],chapterTitle=k=>D.chapters[k]?.title||k,routeName=r=>D.routes[r]||'共通',kindName=k=>k.startsWith('g')?'共通篇':k.startsWith('s')?'共享篇':routeName(D.chapters[k].route)+'线';
const pathNumber=p=>D.paths.filter(x=>x.route===p.route).indexOf(p)+1,pathLabel=p=>'选法 '+pathNumber(p)+(p.choices&&Object.keys(p.choices).length?'（补充分支）':p.variant===0?'（第一组）':'（第二组）');
const closeNav=()=>{document.body.classList.remove('nav-open');$('menuButton').setAttribute('aria-expanded','false')};
function storeProgress(){try{localStorage.setItem(key,JSON.stringify({path:path().id,chapter:state.chapter,scroll:window.scrollY}))}catch{}}
function storePrefs(){try{localStorage.setItem('after-observing-reader-settings',JSON.stringify(prefs))}catch{}}
function applyPrefs(){document.documentElement.style.setProperty('--size',(prefs.size||20)+'px');document.body.classList.toggle('night',!!prefs.night);document.body.classList.toggle('sources',!!prefs.sources);$('fontSize').value=prefs.size||20;$('fontOutput').value=(prefs.size||20)+'px';$('nightToggle').checked=!!prefs.night;$('sourceToggle').checked=!!prefs.sources}
function sourceElement(e){const n=D.nodes[e.n];return make('div',n[0]+':'+n[1],'source')}
function stageName(stage){return {acquaintance:'相识',interest:'在意',dating:'交往中',partner:'交往中'}[stage]||stage||'尚未分线'}
function openContext(index){const p=path(),e=p.events[index],c=ctx(e),body=$('contextBody');body.replaceChildren();body.append(make('p',routeName(p.route)+'线 / '+pathLabel(p)+' / '+chapterTitle(c.chapter)),make('p',c.title+'　'+(c.date||''),'muted'));if(c.route)body.append(make('p','关系：'+stageName(c.stage),'muted'));const ul=make('ol',undefined,'context-choices');let count=0;p.events.slice(0,index).forEach(x=>{if(x.k!=='c')return;const li=make('li');li.append(make('small',chapterTitle(ctx(x).chapter)),make('span',x.o[x.i]));ul.append(li);count++});body.append(count?ul:make('p','还没有作出选择。','muted'));if(prefs.sources){const details=make('details');details.append(make('summary','原生状态与来源'),make('pre',JSON.stringify({path_id:p.id,...c,source:D.nodes[e.n]},null,2),'state-data'));body.append(details)}$('contextDialog').showModal()}
function counterpart(e,selection){for(let pi=0;pi<D.paths.length;pi++){const p=D.paths[pi];if(!e.r&&p.route!==path().route)continue;const ei=p.events.findIndex(x=>x.k==='c'&&x.n===e.n&&x.i===selection);if(ei!==-1)return[pi,ei]}return null}
function drawChoice(e,index){const box=make('div',undefined,'choice');box.id='event-'+e.q;box.append(make('div','这里的选择','choice-title'));const ul=make('ul');e.o.forEach((text,i)=>{const li=make('li',text,i===e.i?'selected':'');ul.append(li)});box.append(ul);const details=make('details');details.append(make('summary','查看已收录的其他选法'));e.o.forEach((text,i)=>{if(i===e.i)return;const other=counterpart(e,i),button=make('button',text,'alternative');button.disabled=!other;if(other)button.onclick=()=>{navigate(other[0],ctx(D.paths[other[0]].events[other[1]]).chapter,other[1],'已切换完整游玩记录，之前的选法也可能不同。可查看本场前情。')};else button.title='尚无这一选法的完整原生记录';details.append(button)});details.append(make('p','切换后保留那条记录自己的前情，不会在当前路径上拼接未运行的组合。','muted'));box.append(details,sourceElement(e));return box}
function navigate(pi,chapter,ei=null,notice=''){state.path=pi;state.chapter=D.paths[pi].order.includes(chapter)?chapter:'g01';draw(notice);closeNav();if(ei!==null){const e=path().events[ei],target=$('event-'+e.q);if(target){target.classList.add('highlight');target.scrollIntoView({block:'center'});setTimeout(()=>target.classList.remove('highlight'),4000)}}else window.scrollTo(0,0);storeProgress()}
function draw(notice=''){
 const p=path();if(!p.order.includes(state.chapter))state.chapter=p.order[0];document.title=chapterTitle(state.chapter)+'｜观测结束以后__VERSION__';
 $('routeTabs').replaceChildren();Object.entries(D.routes).forEach(([route,name])=>{const b=make('button',name);b.setAttribute('aria-pressed',String(p.route===route));b.onclick=()=>{if(route===p.route){closeNav();return}navigate(D.paths.findIndex(x=>x.route===route),state.chapter.startsWith('g')||state.chapter.startsWith('s')?state.chapter:'g01')};$('routeTabs').append(b)});
 $('pathSelect').replaceChildren();D.paths.forEach((r,i)=>{if(r.route!==p.route)return;const o=make('option',pathLabel(r));o.value=i;o.selected=i===state.path;$('pathSelect').append(o)});
 $('chapterList').replaceChildren();p.order.forEach((k,i)=>{const li=make('li'),button=make('button',undefined,k===state.chapter?'current':'');if(k===state.chapter)button.setAttribute('aria-current','page');button.append(make('small',kindName(k)),make('span',chapterTitle(k)));button.onclick=()=>navigate(state.path,k);li.append(button);$('chapterList').append(li)});
 const main=$('reading');main.replaceChildren();const heading=make('div',undefined,'chapter-heading');heading.append(make('p',kindName(state.chapter)+' / 当前路径第 '+(p.order.indexOf(state.chapter)+1)+' 章，共 '+p.order.length+' 章','chapter-meta'),make('h1',chapterTitle(state.chapter)),make('p',routeName(p.route)+'线 · '+pathLabel(p)+(state.chapter.startsWith('s')?'；此处保留这条路线的此前选择。':''),'path-context'));main.append(heading);if(notice)main.append(make('div',notice,'notice'));
 $('sceneList').replaceChildren();let section=null,lastScene=null;const chapterEvents=[];p.events.forEach((e,i)=>{if(ctx(e).chapter===state.chapter)chapterEvents.push([e,i])});
 chapterEvents.forEach(([e,i])=>{const c=ctx(e);if(c.scene!==lastScene){lastScene=c.scene;section=make('section',undefined,'scene');section.id='scene-'+c.scene;const head=make('div',undefined,'scene-head'),h=make('h2',c.title);h.append(make('time',c.date||''));const context=make('button','到这里的前情','context-button');context.onclick=()=>openContext(i);head.append(h,context);section.append(head);main.append(section);const li=make('li'),a=make('a',c.title);a.href='#'+section.id;a.onclick=()=>closeNav();li.append(a);$('sceneList').append(li)}if(e.k==='s'){const item=make('div',undefined,'say '+(e.s?'dialogue':'narration'));item.id='event-'+e.q;if(e.s)item.append(make('span',e.s,'speaker'));item.append(make('p',e.t),sourceElement(e));section.append(item)}else section.append(drawChoice(e,i))});
 $('sceneSummary').textContent='本章场景（'+$('sceneList').children.length+'）';const controls=make('div',undefined,'chapter-controls'),ci=p.order.indexOf(state.chapter);for(const [delta,label] of [[-1,'上一章'],[1,'下一章']]){const next=p.order[ci+delta],b=make('button');b.disabled=!next;b.append(make('small',label),make('span',next?chapterTitle(next):delta===1?'本条路线完':'已在开篇'));if(next)b.onclick=()=>navigate(state.path,next);controls.append(b)}main.append(controls);$('evidence').textContent='50 章 / '+D.paths.length+' 条完整游玩记录 / 原生正文并集 '+D.union.characters.toLocaleString('zh-CN')+' 字';updateProgress()
}
function updateProgress(){const total=document.documentElement.scrollHeight-innerHeight;$('progress').style.width=(total>0?Math.min(100,scrollY/total*100):0)+'%'}
function catalog(){const body=$('catalogBody');body.replaceChildren();$('catalogContext').textContent='共通篇与共享篇使用当前的'+routeName(path().route)+'线前情；个人篇会切换到对应路线。';const groups=[['共通篇',Object.keys(D.chapters).filter(k=>k.startsWith('g'))],['共享篇',Object.keys(D.chapters).filter(k=>k.startsWith('s'))],...Object.entries(D.routes).map(([r,n])=>[n+'线',Object.keys(D.chapters).filter(k=>D.chapters[k].route===r)])];groups.forEach(([name,keys])=>{const section=make('section',undefined,'catalog-group'),grid=make('div',undefined,'catalog-grid');section.append(make('h3',name));keys.forEach(k=>{const b=make('button',chapterTitle(k));b.onclick=()=>{let pi=state.path;const route=D.chapters[k].route;if(D.routes[route]&&route!==path().route)pi=D.paths.findIndex(p=>p.route===route);$('catalogDialog').close();navigate(pi,k)};grid.append(b)});section.append(grid);body.append(section)});$('catalogDialog').showModal()}
function excerpt(text,query){const p=make('p'),at=text.toLocaleLowerCase().indexOf(query.toLocaleLowerCase());if(at<0){p.textContent=text.slice(0,150);return p}const start=Math.max(0,at-40),end=Math.min(text.length,at+query.length+80);if(start)p.append(document.createTextNode('…'));p.append(document.createTextNode(text.slice(start,at)),make('mark',text.slice(at,at+query.length)),document.createTextNode(text.slice(at+query.length,end)+(end<text.length?'…':'')));return p}
function moreSearch(){const query=$('searchInput').value.trim(),end=Math.min(searchShown+100,searchMatches.length),results=$('searchResults');for(let n=searchShown;n<end;n++){const [pi,ei,text]=searchMatches[n],p=D.paths[pi],e=p.events[ei],c=ctx(e),b=make('button',undefined,'search-result');b.append(make('small',routeName(p.route)+'线 / '+pathLabel(p)+' / '+chapterTitle(c.chapter)+' / '+c.title+(e.s?' / '+e.s:'')),excerpt(text,query));b.onclick=()=>{$('searchDialog').close();navigate(pi,c.chapter,ei)};results.append(b)}searchShown=end;$('searchMore').hidden=end===searchMatches.length}
function search(){const query=$('searchInput').value.trim(),scope=$('searchScope').value;searchMatches=[];searchShown=0;$('searchResults').replaceChildren();$('searchMore').hidden=true;if(!query){$('resultCount').textContent='输入关键词即可搜索，选择文字也可搜索。';return}const seen=new Set(),q=query.toLocaleLowerCase();D.paths.forEach((p,pi)=>{if(scope==='route'&&p.route!==path().route||scope==='path'&&pi!==state.path)return;p.events.forEach((e,ei)=>{const text=e.k==='s'?e.t:e.o.join(' / '),all=(e.s||'')+' '+text;if(!all.toLocaleLowerCase().includes(q))return;const k=p.route+'|'+e.n+'|'+text;if(seen.has(k))return;seen.add(k);searchMatches.push([pi,ei,text])})});$('resultCount').textContent=searchMatches.length?'找到 '+searchMatches.length+' 处。同一条路线中相同位置与文字合并显示，打开后可查看完整前情。':'没有找到；可试更短的词，或切换搜索范围。';moreSearch()}
$('pathSelect').onchange=e=>navigate(Number(e.target.value),state.chapter,null,'已切换完整游玩记录，请按需要查看本场前情。');$('menuButton').onclick=()=>{const open=document.body.classList.toggle('nav-open');$('menuButton').setAttribute('aria-expanded',String(open))};$('veil').onclick=closeNav;$('catalogButton').onclick=catalog;
$('searchButton').onclick=()=>{const selection=String(window.getSelection()).trim();if(selection&&selection.length<=120)$('searchInput').value=selection;$('searchDialog').showModal();search();$('searchInput').focus()};$('settingsButton').onclick=()=>$('settingsDialog').showModal();$('creditsButton').onclick=()=>$('creditsDialog').showModal();document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>b.closest('dialog').close());
$('fontSize').oninput=e=>{prefs.size=Number(e.target.value);applyPrefs();storePrefs()};$('nightToggle').onchange=e=>{prefs.night=e.target.checked;applyPrefs();storePrefs()};$('sourceToggle').onchange=e=>{prefs.sources=e.target.checked;applyPrefs();storePrefs()};$('searchInput').oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(search,160)};$('searchScope').onchange=search;$('searchMore').onclick=moreSearch;
window.addEventListener('scroll',()=>{updateProgress();clearTimeout(saveTimer);saveTimer=setTimeout(storeProgress,250)},{passive:true});window.addEventListener('beforeunload',storeProgress);document.addEventListener('keydown',e=>{if(e.key==='/'&&!e.ctrlKey&&!e.metaKey&&!['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName)&&!document.querySelector('dialog[open]')){e.preventDefault();$('searchButton').click()}if(e.key==='Escape')closeNav()});
$('fingerprints').textContent='故事稿 SHA-256: '+D.fingerprint+'\n运行工程 SHA-256: '+D.runtime;applyPrefs();draw();if(saved.scroll)requestAnimationFrame(()=>window.scrollTo(0,saved.scroll));document.fonts.ready.then(()=>{if(saved.scroll)window.scrollTo(0,saved.scroll);updateProgress()});
</script></body></html>'''


def embedded_font(data_text):
    try:
        from fontTools.ttLib import TTFont
        from fontTools import subset
    except ImportError as exc:
        raise ValueError('生成阅读器需要本地 fontTools；不会联网加载字体') from exc
    face = TTFont(PROJECT / 'game/fonts/NotoSansCJKsc-Regular.otf')
    options = subset.Options()
    options.layout_features = ['*']
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=data_text + TEMPLATE)
    subsetter.subset(face)
    names = {1: 'After Observing Reader', 2: 'Regular', 3: 'AfterObservingReader-Subset', 4: 'After Observing Reader Regular', 6: 'AfterObservingReader-Regular', 16: 'After Observing Reader', 17: 'Regular'}
    for record in face['name'].names:
        if record.nameID in names:
            record.string = names[record.nameID].encode(record.getEncoding(), errors='replace')
    if 'CFF ' in face:
        # OTF carries a second family identity inside CFF, independent of 'name'.
        cff = face['CFF '].cff
        cff.fontNames = ['AfterObservingReader-Regular']
        for top in cff.topDictIndex:
            top.FullName = 'After Observing Reader Regular'
            top.FamilyName = 'After Observing Reader'
    face.flavor = 'woff'
    stream = io.BytesIO()
    face.save(stream)
    face.close()
    encoded = base64.b64encode(stream.getvalue()).decode('ascii')
    return "@font-face{font-family:AfterObservingReader;src:url('data:font/woff;base64," + encoded + "') format('woff');font-display:swap}", len(stream.getvalue())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=WORK / 'playthrough')
    parser.add_argument('--output', type=Path, default=DIST / ('AfterObserving-'+VERSION+'-reader.html'))
    parser.add_argument('--check', action='store_true', help='只校验真实导出，不写阅读器')
    args = parser.parse_args()
    try:
        data = load_native(args.input.resolve())
        if args.check:
            print(json.dumps({'valid': True, 'chapters': len(data['chapters']), 'paths': len(data['paths']), 'characters': data['union']['characters']}, ensure_ascii=False))
            return
        raw = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        font, font_bytes = embedded_font(raw)
        license_text = (PROJECT / 'game/fonts/LICENSE.txt').read_text(encoding='utf8')
        safe_data = raw.replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
        # Substitute once: captured text cannot become a later template marker.
        substitutions = {'__VERSION__': html.escape(VERSION), '__FONT__': font, '__LICENSE__': html.escape(license_text), '__DATA__': safe_data}
        document = re.sub(r'__VERSION__|__FONT__|__LICENSE__|__DATA__', lambda match: substitutions[match[0]], TEMPLATE)
        require(source_fingerprint() == data['fingerprint'] and runtime_digest() == data['runtime'], '生成字体期间工程发生变化；请在冻结后重新生成')
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        temp = output.with_suffix(output.suffix + '.tmp')
        temp.write_text(document, encoding='utf8')
        temp.replace(output)
        report = {'output': str(output), 'bytes': output.stat().st_size, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'source_fingerprint': data['fingerprint'], 'runtime_fingerprint': data['runtime'], 'chapter_count': len(data['chapters']), 'native_paths': [p['id'] for p in data['paths']], 'native_union': data['union'], 'font_bytes': font_bytes, 'native_text_only': True, 'generated_utc': datetime.now(timezone.utc).isoformat()}
        (PROJECT / 'docs/reader-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        print(json.dumps({'output': str(output), 'bytes': report['bytes'], 'chapters': 50, 'paths': len(data['paths']), 'characters': data['union']['characters']}, ensure_ascii=False))
    except (ValueError, OSError) as exc:
        print('阅读器未生成：' + str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == '__main__':
    main()
