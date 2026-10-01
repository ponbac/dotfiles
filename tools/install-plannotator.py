#!/usr/bin/env python3
"""Run the official, version-matched installer after mise installs Plannotator."""
import argparse
import datetime
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', help='Concrete release installed by mise')
    parser.add_argument('install_path', type=Path, help='MISE_TOOL_INSTALL_PATH')
    args = parser.parse_args()
    version = args.version.removeprefix('v')
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        parser.error('Expected a concrete stable release version')
    binary = args.install_path / 'plannotator'
    expected = 'plannotator ' + version
    actual = subprocess.check_output([str(binary), '--version'], text=True).strip()
    if actual != expected:
        raise SystemExit(f'Mise binary version mismatch: expected {expected}, got {actual}')

    home = Path.home()
    # Backup locally changed/generated skills and shared configs before the
    # upstream installer updates them. Never sync these backups or credentials.
    names = {'.local/bin/plannotator', '.plannotator/install-prefs',
             '.claude/settings.json', '.claude/settings.local.json',
             '.codex/hooks.json', '.codex/config.toml', '.pi/agent/settings.json',
             '.config/opencode/opencode.json', '.config/opencode/opencode.jsonc',
             '.gemini/settings.json', '.gemini/policies/plannotator.toml',
             '.kiro/agents/plannotator.json', '.vibe/hooks.toml'}
    for directory in ['.agents/skills', '.claude/skills', '.claude/commands',
                      '.config/opencode/commands', '.config/opencode/command',
                      '.gemini/commands', '.kiro/skills', '.vibe/skills']:
        names.update(str(p.relative_to(home)) for p in (home / directory).glob('plannotator*'))
    backup = home / '.local/state/plannotator-install-backups' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True, mode=0o700)
    manifest = []
    for name in sorted(names):
        source = home / name
        exists = source.exists() or source.is_symlink()
        manifest.append({'path': name, 'existed': exists})
        if exists:
            target = backup / name
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if source.is_symlink():
                target.symlink_to(source.readlink())
            elif source.is_dir():
                shutil.copytree(source, target, symlinks=True)
            else:
                shutil.copy2(source, target)
                target.chmod(0o600)
    (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Plannotator installer recovery backup:', backup, flush=True)

    # Fetch from the same release tag as the binary, not the mutable website
    # installer. There is no upstream integration-only mode: it also installs a
    # matching ~/.local/bin/plannotator. Mise and that copy must stay in lockstep.
    with tempfile.TemporaryDirectory(prefix='plannotator-installer-') as directory:
        installer = Path(directory) / 'install.sh'
        subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location',
                        '--output', str(installer),
                        f'https://raw.githubusercontent.com/backnotprop/plannotator/v{version}/scripts/install.sh'],
                       check=True)
        subprocess.run(['bash', str(installer), '--version', 'v' + version,
                        '--non-interactive', '--no-minimal', '--verify-attestation'], check=True)
    actual = subprocess.check_output([str(home / '.local/bin/plannotator'), '--version'], text=True).strip()
    if actual != expected:
        raise SystemExit(f'Installer binary version mismatch: expected {expected}, got {actual}')


if __name__ == '__main__':
    main()
