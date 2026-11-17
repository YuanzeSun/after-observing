"""Build and test the optional CG-only patch against isolated native profiles."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
from paths import PROJECT as R, WORK, SDK, DIST, VERSION, PACKAGE

PATCH = 'game/zz_after_observing_cg_unlock.rpy'
SOURCE = R / 'extras/cg-unlock'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_patch(destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for name in ('README.txt', PATCH):
            bundle.write(SOURCE / name, name)
    with zipfile.ZipFile(destination) as bundle:
        assert set(bundle.namelist()) == {'README.txt', PATCH}
        assert bundle.read(PATCH) == (SOURCE / PATCH).read_bytes()
    return destination


def verify():
    if not os.environ.get('DISPLAY'):
        raise SystemExit('Native patch verification needs DISPLAY')
    q = WORK / 'qa/cg-patch'
    if q.exists():
        shutil.rmtree(q)
    project = q / 'project'
    game = project / 'game'
    shutil.copytree(R / 'game', game, ignore=shutil.ignore_patterns(
        'images', 'audio', 'fonts', 'saves', 'cache', '*.rpyc', '*.rpyb'))
    for name in ('images', 'audio', 'fonts'):
        (game / name).symlink_to(R / 'game' / name, target_is_directory=True)
    shutil.copy2(R / 'tests/fixtures/cg_unlock.rpy', game / 'author_cg_patch_tests.rpy')
    current_core = (game / 'core.rpy').read_text()
    # The base game change in this patch release is the displayed version only.
    (game / 'core.rpy').write_text(current_core.replace(
        'define config.version = "' + VERSION + '"', 'define config.version = "1.1"', 1))
    archive = write_patch(q / (PACKAGE + '-cg-unlock.zip'))
    results = []

    def install(enabled):
        target = project / PATCH
        target.unlink(missing_ok=True)
        target.with_suffix('.rpyc').unlink(missing_ok=True)
        if enabled:
            with zipfile.ZipFile(archive) as bundle:
                target.write_bytes(bundle.read(PATCH))

    def run(name, testcase, profile, version='1.1'):
        screens = q / 'screens' / name
        screens.mkdir(parents=True)
        env = os.environ.copy()
        env.update(AFTER_OBSERVING_AUTHOR='1', SDL_AUDIODRIVER='dummy',
                   LIBGL_ALWAYS_SOFTWARE='1', AO_CG_PATCH_SCREENS=str(screens),
                   AO_CG_PATCH_VERSION=version)
        log = q / (name + '.log')
        with log.open('w') as output:
            completed = subprocess.run([str(SDK / 'renpy.sh'), str(project), '--savedir',
                str(q / 'profiles' / profile), 'test', 'cg_patch.' + testcase,
                '--overwrite-screenshots'], env=env, stdout=output, stderr=subprocess.STDOUT)
        text = log.read_text()
        passed = completed.returncode == 0 and '[rpytest] Status: PASSED' in text
        results.append({'case': name, 'passed': passed, 'version': version, 'log': str(log)})
        print(name + ': ' + ('passed' if passed else text[-4000:]), flush=True)
        if not passed:
            raise SystemExit('Native CG patch check failed: ' + name)

    install(False)
    run('unpatched-locked', 'locked', 'unpatched')
    install(True)
    run('fresh-installed', 'fresh', 'fresh')
    install(False)
    run('fresh-restarted-without-patch', 'fresh', 'fresh')
    run('existing-1.1-seed', 'seed', 'existing')
    before = {str(p.relative_to(q)): sha(p) for p in q.rglob('*.save')}
    assert before, 'Expected a real player save before installing the patch'
    install(True)
    run('existing-1.1-patched', 'existing', 'existing')
    (game / 'core.rpy').write_text(current_core)
    (game / 'core.rpyc').unlink(missing_ok=True)
    run('existing-upgraded-to-' + VERSION, 'existing', 'existing', VERSION)
    after = {str(p.relative_to(q)): sha(p) for p in q.rglob('*.save')}
    assert before == after, 'Patch changed player save files'
    from release import runtime_digest
    report = {'passed': True, 'version': VERSION, 'runtime_sha256': runtime_digest(), 'patch_sha256': sha(SOURCE / PATCH),
              'fixture_sha256': sha(R / 'tests/fixtures/cg_unlock.rpy'),
              'archive_sha256': sha(archive), 'cg_count': 32, 'save_files_unchanged': True,
              'cases': results}
    (R / 'docs/cg-patch-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


def bundle():
    from release import runtime_digest
    report = json.loads((R / 'docs/cg-patch-verification.json').read_text())
    assert report['passed'] and report['version'] == VERSION
    assert report['runtime_sha256'] == runtime_digest()
    assert report['patch_sha256'] == sha(SOURCE / PATCH)
    assert report['fixture_sha256'] == sha(R / 'tests/fixtures/cg_unlock.rpy')
    return write_patch(DIST / (PACKAGE + '-cg-unlock.zip'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['verify', 'bundle'])
    args = parser.parse_args()
    globals()[args.command]()
