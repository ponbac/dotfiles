#!/usr/bin/env python3
"""Reconcile fixed Pi packages and the extension matching Plannotator's installer."""
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess


def main():
    home = Path.home()
    override = os.environ.get('PI_CODING_AGENT_DIR')
    if override and Path(override).expanduser().resolve() != (home / '.pi/agent').resolve():
        raise SystemExit('Review PI_CODING_AGENT_DIR before reconciling home-scoped packages')
    lock = home / '.local/state/agent-integration-update.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        reconcile(home)


def reconcile(home):
    settings = json.loads((home / '.pi/agent/settings.json').read_text())
    for entry in settings.get('packages', []):
        configured = entry['source'] if isinstance(entry, dict) else entry
        source = configured
        if not source.startswith('npm:'):
            raise SystemExit('Review non-npm package before provisioning: ' + source)
        if source == 'npm:@plannotator/pi-extension' or source.startswith('npm:@plannotator/pi-extension@'):
            # The verified installer copy reflects the latest integration update,
            # even if mise has not finished registering that version yet. Never
            # invoke mise exec while holding the lock its postinstall also takes.
            cli = subprocess.check_output([str(home / '.local/bin/plannotator'), '--version'],
                                          text=True).strip()
            match = re.fullmatch(r'plannotator (\d+\.\d+\.\d+)', cli)
            if not match:
                raise SystemExit('Unexpected Plannotator version: ' + cli)
            source = 'npm:@plannotator/pi-extension@' + match[1]
        name, separator, version = source[4:].rpartition('@')
        if not separator or not name or not version or version in ('latest', '*'):
            raise SystemExit('Package must have an explicit version: ' + source)
        package = home / '.pi/agent/npm/node_modules' / name / 'package.json'
        installed = json.loads(package.read_text()).get('version') if package.exists() else None
        if installed != version or configured != source:
            subprocess.run(['pi', 'install', source, '--no-approve'], check=True)
        actual = json.loads(package.read_text()).get('version') if package.exists() else None
        if actual != version:
            raise SystemExit(f'Package reconciliation failed: {name}, expected {version}, got {actual}')
        print(f'{name}: {version} verified')


if __name__ == '__main__':
    main()
