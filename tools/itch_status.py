"""Wait for itch.io to finish processing both uploaded release channels."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import zipfile


def channel_status(result, target, version):
    if result.get('target') != target:
        raise ValueError('itch.io returned a different project')
    channels = {c['name']: c for c in result['channels']}
    rows = []
    ready = True
    for name in ('windows', 'linux'):
        channel = channels.get(name, {})
        head = channel.get('head') or {}
        pending = channel.get('pending') or {}
        for build in (head, pending):
            if build.get('userVersion') == version and build.get('state') in ('failed', 'cancelled', 'canceled'):
                raise ValueError('itch.io processing failed for ' + name)
        done = head.get('state') == 'completed' and head.get('userVersion') == version and not pending
        ready = ready and done
        rows.append({'channel': name, 'build': head.get('id'), 'version': head.get('userVersion'),
                     'state': head.get('state'), 'pending': pending.get('state')})
    return ready, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*/[a-z0-9][a-z0-9_-]*', args.target):
        raise SystemExit('Invalid itch.io target')
    if not re.fullmatch(r'v[0-9][A-Za-z0-9.+_-]*', args.tag):
        raise SystemExit('Invalid release tag')
    if not os.environ.get('BUTLER_API_KEY'):
        raise SystemExit('BUTLER_API_KEY is required')
    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / '.github/toolchain.json').read_text())
    work = root / '.build/itch-status'
    work.mkdir(parents=True, exist_ok=True)
    archive = work / 'butler.zip'
    subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location', '--retry', '3',
                    '--limit-rate', '3000000', lock['butler_url'], '--output', str(archive)], check=True)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != lock['butler_sha256']:
        raise SystemExit('Butler checksum mismatch')
    executable = work / 'butler'
    with zipfile.ZipFile(archive) as bundle:
        executable.write_bytes(bundle.read('butler'))
    executable.chmod(0o755)
    deadline = time.monotonic() + 2400
    previous = None
    while time.monotonic() < deadline:
        command = subprocess.run([str(executable), '--json', 'status', args.target],
                                 capture_output=True, text=True, timeout=60, check=True)
        results = [json.loads(line) for line in command.stdout.splitlines() if line.strip().startswith('{')]
        values = [r['value'] for r in results if r.get('type') == 'result']
        if len(values) != 1:
            raise SystemExit('Butler did not return one channel status result')
        ready, rows = channel_status(values[0], args.target, args.tag[1:])
        if rows != previous:
            print(json.dumps(rows), flush=True)
            previous = rows
        if ready:
            print('Verified completed Windows and Linux builds for ' + args.tag, flush=True)
            return
        time.sleep(20)
    raise SystemExit('Timed out waiting for the expected itch.io channel versions')


if __name__ == '__main__':
    main()
