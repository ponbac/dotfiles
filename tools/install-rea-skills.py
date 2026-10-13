#!/usr/bin/env python3
"""Install only REA's shared and Claude Code skills using the installed CLI."""
import argparse
import fcntl
import json
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile


SKILL_PATHS = ('.agents/skills/reverse-engineer-anything',
               '.claude/skills/reverse-engineer-anything')


def reject_links(path, recursive=False):
    # Inspect ancestors without resolve(): resolving would hide source symlinks.
    for entry in (*reversed(path.parents), path):
        if entry.is_symlink():
            raise RuntimeError('REA skill install refused: symlink path')
    if recursive and path.is_dir():
        for entry in path.iterdir():
            reject_links(entry, recursive=True)
    elif path.exists() and not path.is_dir() and not stat.S_ISREG(path.stat().st_mode):
        raise RuntimeError('REA skill install refused: non-regular file')


def setup(binary, home, dry_run):
    # Explicit skill-client scope makes upstream clientIds=[]; never select MCP
    # clients or native providers. Capture output because discovery may be private.
    command = [str(binary), 'setup', '--skill-client', 'shared',
               '--skill-client', 'claude_code', '--yes', '--json']
    if dry_run:
        command.append('--dry-run')
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f'REA setup failed (exit {result.returncode})')
    try:
        report = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise RuntimeError('REA setup failed: invalid JSON') from None
    expected_status = 'planned' if dry_run else 'ready'
    if not isinstance(report, dict) or report.get('status') != expected_status:
        raise RuntimeError('REA setup failed: unsuccessful status')
    actions = report.get('plannedActions')
    targets = {str(home / name) for name in SKILL_PATHS}
    # SetupPlan.js publishes action objects, not strings. Fail closed if a
    # future release changes scope, shape, or destination.
    if not isinstance(actions, list) or any(
        not isinstance(action, dict) or action.get('kind') != 'install_skill'
        or not isinstance(action.get('target'), str) or action['target'] not in targets
        or action.get('external') is not False
        or action.get('operation') != 'install'
        for action in actions
    ):
        raise RuntimeError('REA setup refused: unexpected action')
    applied = report.get('appliedActions')
    if not isinstance(applied, list) or any(action != 'installed_skill' for action in applied):
        raise RuntimeError('REA setup refused: unexpected applied action')
    if dry_run and applied:
        raise RuntimeError('REA setup refused: dry-run applied actions')
    return actions


def backup_skills(home):
    root = home / '.local/state/rea-skill-install-backups'
    reject_links(root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    backup = Path(tempfile.mkdtemp(prefix='install-', dir=root))
    manifest = []
    for name in SKILL_PATHS:
        source = home / name
        existed = source.exists()
        manifest.append({'path': name, 'existed': existed})
        if existed:
            target = backup / name
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            # Never dereference a link while backing up, even though the
            # preflight rejects linked skill paths before calling setup.
            shutil.copytree(source, target, symlinks=True)
    manifest_path = backup / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    manifest_path.chmod(0o600)
    print('REA skill backup:', backup, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('installation', type=Path, help='Absolute mise installation directory or REA executable')
    args = parser.parse_args()
    if not args.installation.is_absolute():
        parser.error('Expected an absolute REA installation path')
    home = Path.home()
    try:
        binary = args.installation
        if binary.is_dir():
            # mise's npm backend can use npm (bin/) or aube/pnpm (.bin/).
            binary = next((candidate for candidate in (
                binary / 'bin/rea', binary / 'node_modules/.bin/rea'
            ) if candidate.is_file()), None)
            if binary is None:
                raise RuntimeError('REA skill install failed: executable missing from installation')
        lock = home / '.local/state/agent-integration-update.lock'
        reject_links(lock)
        lock.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with lock.open('a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            for name in SKILL_PATHS:
                skill = home / name
                reject_links(skill, recursive=True)
                if skill.exists() and not skill.is_dir():
                    raise RuntimeError('REA skill install refused: skill root is not a directory')
            actions = setup(binary, home, dry_run=True)
            if not actions:
                print('REA skills: unchanged')
                return
            backup_skills(home)
            setup(binary, home, dry_run=False)
            print('REA skills: ready')
    except RuntimeError as error:
        raise SystemExit(str(error)) from None
    except OSError:
        raise SystemExit('REA skill install failed: filesystem or process error') from None


if __name__ == '__main__':
    main()
