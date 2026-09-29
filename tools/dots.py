#!/usr/bin/env python3
"""Git transport for the chezmoi source. Never imports files from the live home."""
import argparse
import datetime
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
BRANCH = 'master'
REMOTE = 'origin/' + BRANCH


def git(*args, capture=True, env=None, check=True):
    return subprocess.run(['git', '-C', str(SOURCE), *args], check=check,
                          text=True, capture_output=capture, env=env)


def value(*args):
    return git(*args).stdout.strip()


def fail(message):
    raise SystemExit(message)


def confirm(message, yes):
    if yes:
        return
    if not sys.stdin.isatty():
        fail('Confirmation requires a terminal; pass --yes after reviewing the changes.')
    if input(message + ' [y/N] ').strip().lower() not in ('y', 'yes'):
        fail('Cancelled.')


def working_tree():
    # Independent index: inspect the proposed source tree without changing staging.
    with tempfile.TemporaryDirectory(prefix='dotpush-index-') as tmp:
        env = os.environ.copy()
        env['GIT_INDEX_FILE'] = str(Path(tmp) / 'index')
        head = git('rev-parse', '--verify', 'HEAD', check=False)
        if head.returncode == 0:
            git('read-tree', 'HEAD', env=env)
        git('add', '-A', env=env)
        return git('write-tree', env=env).stdout.strip()


def has_head():
    return git('rev-parse', '--verify', 'HEAD', check=False).returncode == 0


def ancestor(first, second):
    result = git('merge-base', '--is-ancestor', first, second, check=False)
    if result.returncode not in (0, 1):
        fail('Cannot inspect Git ancestry; no reset or merge attempted.')
    return result.returncode == 0


def adopt_matching_bootstrap():
    """Adopt a published tree only when source contents match it exactly."""
    if working_tree() != value('rev-parse', REMOTE + '^{tree}'):
        return False
    if has_head() and not ancestor('HEAD', REMOTE):
        return False
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = Path.home() / '.local/state/dotsync-bootstrap-backups' / stamp
    backup.mkdir(parents=True, mode=0o700)
    shutil.copytree(SOURCE / '.git', backup / 'git', symlinks=True)
    # Only branch/index metadata changes: source files are already the exact
    # published tree. The original Git/index state is preserved above.
    git('reset', '--mixed', REMOTE)
    git('branch', '--set-upstream-to=' + REMOTE, BRANCH)
    print('Adopted matching published setup; Git metadata backup:', backup, flush=True)
    return True


def fetch():
    if value('symbolic-ref', '--short', 'HEAD') != BRANCH:
        fail('Switch the dotfiles repository to master first; detached/other branches are not modified.')
    git('fetch', 'origin', capture=False)
    if git('rev-parse', '--verify', REMOTE, check=False).returncode:
        fail('origin/master is missing; initialize/review the remote manually.')


def sync(args):
    fetch()
    dirty = bool(value('status', '--porcelain'))
    if dirty or not has_head():
        if working_tree() != value('rev-parse', REMOTE + '^{tree}'):
            fail('Unpublished source changes: nothing overwritten. Run dotpush on the originating machine first,\n'
                 'or review/reconcile this source with `chezmoi cd` and `git status`. No stash/reset was performed.')
        confirm('Adopt the published version that exactly matches this source?', args.yes)
        if not adopt_matching_bootstrap():
            fail('Local history diverges. Reconcile manually; nothing reset.')
    else:
        if not ancestor('HEAD', REMOTE):
            fail('Local commits are ahead of or diverge from origin/master. Run dotpush or reconcile manually.')
        git('merge', '--ff-only', REMOTE, capture=False)
    # Print filenames only. Full modify-template diffs may contain local secrets.
    subprocess.run(['chezmoi', 'status', '--no-pager'], check=True)
    confirm('Apply this configuration and reconcile pinned Pi packages on this machine?', args.yes)
    subprocess.run([sys.executable, str(SOURCE / 'tools/deploy.py'), os.uname().nodename,
                    '--apply', '--bootstrap'], check=True)
    print('Synced. Reload/restart running agents to pick up configuration changes.')


def push(args):
    fetch()
    if not has_head():
        fail('This source has no local commit yet. Publish from the workstation first, then run dotsync here.')
    if not ancestor(REMOTE, 'HEAD'):
        fail('origin/master has changes missing locally. Review and run dotsync before publishing; no rebase or force-push performed.')
    status = value('status', '--short')
    print(status or 'No uncommitted source changes.', flush=True)
    print('Only the chezmoi source is published. Live home files and the wallpaper repo are not imported.', flush=True)
    changed = working_tree() != value('rev-parse', 'HEAD^{tree}')
    ahead = value('rev-list', '--count', REMOTE + '..HEAD')
    if not changed and ahead == '0':
        print('Already up to date; nothing to push.')
        return
    confirm('Commit these source changes (if any) and push to origin/master?', args.yes)
    if changed:
        git('add', '-A', capture=False)
        git('commit', '-m', args.message, capture=False)
    # Ordinary push rejects concurrent remote changes; never force or auto-rebase.
    git('push', '--set-upstream', 'origin', BRANCH, capture=False)
    print('Published. Run dotsync on the other machines. Your local live config is not automatically reapplied.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('sync', 'push'):
        p = sub.add_parser(name)
        p.add_argument('-y', '--yes', action='store_true', help='Approve without interactive prompts')
        if name == 'push':
            p.add_argument('-m', '--message', default='chore(dotfiles): sync configuration', help='Commit message')
    args = parser.parse_args()
    if not (SOURCE / '.git').is_dir():
        fail('Expected a normal Git repository in the chezmoi source.')
    if any((SOURCE / '.git' / marker).exists() for marker in
           ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply')):
        fail('Finish the in-progress Git operation before syncing or publishing.')
    actual = subprocess.check_output(['chezmoi', 'source-path'], text=True).strip()
    if Path(actual).resolve() != SOURCE:
        fail('This script is not running from the active chezmoi source.')
    (sync if args.command == 'sync' else push)(args)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as exc:
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        raise SystemExit(exc.returncode)
