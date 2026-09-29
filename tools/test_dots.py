"""CLI integration tests; all Git writes and deployment requests stay in temp dirs.

Run: python3 -B -m unittest discover -s tools -p 'test_dots.py' -v
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


DOTS = Path(__file__).with_name('dots.py')


class DotsCLIIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-cli-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.source = self.root / 'source'
        self.remote = self.root / 'remote.git'
        self.peer = self.root / 'peer'
        self.apply_log = self.root / 'apply.json'
        self.chezmoi_log = self.root / 'chezmoi.jsonl'
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        # Do not inherit Git identity, repository/index overrides, hooks, signing,
        # credentials, or transport configuration from the developer's session.
        self.env = {
            'PATH': str(bin_dir) + os.pathsep + os.defpath,
            'HOME': str(self.home),
            'XDG_CONFIG_HOME': str(self.home / '.config'),
            'XDG_STATE_HOME': str(self.home / '.local/state'),
            'TMPDIR': str(self.root),
            'LC_ALL': 'C',
            'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': os.devnull,
            'GIT_ALLOW_PROTOCOL': 'file',
            'GIT_TERMINAL_PROMPT': '0',
            'GIT_AUTHOR_NAME': 'Dots Test',
            'GIT_AUTHOR_EMAIL': 'dots@example.invalid',
            'GIT_COMMITTER_NAME': 'Dots Test',
            'GIT_COMMITTER_EMAIL': 'dots@example.invalid',
            'PYTHONDONTWRITEBYTECODE': '1',
            'TEST_SOURCE': str(self.source),
            'TEST_APPLY_LOG': str(self.apply_log),
            'TEST_CHEZMOI_LOG': str(self.chezmoi_log),
        }
        chezmoi = bin_dir / 'chezmoi'
        chezmoi.write_text(
            f'#!{sys.executable}\n'
            'import json, os, sys\n'
            'args = sys.argv[1:]\n'
            'with open(os.environ["TEST_CHEZMOI_LOG"], "a") as log:\n'
            '    log.write(json.dumps(args) + "\\n")\n'
            'if args == ["source-path"]:\n'
            '    print(os.environ["TEST_SOURCE"])\n'
            'elif args == ["status", "--no-pager"]:\n'
            '    print(" M .config/example")\n'
            'else:\n'
            '    sys.exit("Unexpected chezmoi request: " + repr(args))\n'
        )
        chezmoi.chmod(0o755)
        self.git(self.root, 'init', '--bare', '--initial-branch=master', str(self.remote))
        self.git(self.root, 'clone', str(self.remote), str(self.source))
        (self.source / 'tools').mkdir()
        shutil.copy2(DOTS, self.source / 'tools/dots.py')
        (self.source / 'tools/deploy.py').write_text(
            'import json, os, sys\n'
            'from pathlib import Path\n'
            'Path(os.environ["TEST_APPLY_LOG"]).write_text(json.dumps(sys.argv[1:]))\n'
        )
        (self.source / 'dot_example').write_bytes(b'original config\n')
        self.commit(self.source, 'initial fixture')
        self.git(self.source, 'push', '-u', 'origin', 'master')
        self.git(self.root, 'clone', str(self.remote), str(self.peer))

    def git(self, repo, *args):
        result = subprocess.run(
            ['git', '-C', str(repo), *args], env=self.env,
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def commit(self, repo, message):
        self.git(repo, 'add', '-A')
        self.git(repo, 'commit', '-m', message)
        return self.git(repo, 'rev-parse', 'HEAD')

    def publish_update(self):
        (self.peer / 'dot_example').write_bytes(b'published config\n')
        tip = self.commit(self.peer, 'remote update')
        self.git(self.peer, 'push', 'origin', 'master')
        return tip

    def cli(self, command, *args, succeeds=True):
        result = subprocess.run(
            [sys.executable, str(self.source / 'tools/dots.py'), command, '--yes', *args],
            cwd=self.home, env=self.env, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=30,
        )
        output = result.stdout + result.stderr
        if succeeds:
            self.assertEqual(result.returncode, 0, output)
        else:
            self.assertNotEqual(result.returncode, 0, output)
        return output

    def source_bytes(self):
        return {
            str(path.relative_to(self.source)): path.read_bytes()
            for path in self.source.rglob('*')
            if path.is_file() and '.git' not in path.relative_to(self.source).parts
        }

    def assert_applied(self):
        self.assertTrue(self.apply_log.exists(), 'deploy was not requested')
        self.assertEqual(json.loads(self.apply_log.read_text()),
                         [os.uname().nodename, '--apply', '--bootstrap'])
        calls = [json.loads(line) for line in self.chezmoi_log.read_text().splitlines()]
        self.assertEqual(calls, [['source-path'], ['status', '--no-pager']])

    def assert_refuses_without_changes(self, command, diagnostic):
        files = self.source_bytes()
        head = self.git(self.source, 'rev-parse', 'HEAD')
        remote_head = self.git(self.remote, 'rev-parse', 'master')
        index = (self.source / '.git/index').read_bytes()
        output = self.cli(command, succeeds=False)
        self.assertIn(diagnostic, output)
        self.assertEqual(self.source_bytes(), files)
        self.assertEqual(self.git(self.source, 'rev-parse', 'HEAD'), head)
        self.assertEqual(self.git(self.remote, 'rev-parse', 'master'), remote_head)
        self.assertEqual((self.source / '.git/index').read_bytes(), index)
        self.assertFalse(self.apply_log.exists())
        self.assertFalse((self.home / '.local/state/dotsync-bootstrap-backups').exists())

    def test_push_commits_source_only_not_live_home(self):
        (self.home / '.example').write_bytes(b'private live config\n')
        (self.home / 'unrelated-secret').write_bytes(b'never publish me\n')
        (self.source / 'dot_example').write_bytes(b'edited source\n')
        (self.source / 'dot_new').write_bytes(b'new source file\n')
        self.cli('push', '--message', 'test: publish source')
        self.assertEqual(self.git(self.remote, 'show', 'master:dot_example'), 'edited source')
        self.assertEqual(self.git(self.remote, 'show', 'master:dot_new'), 'new source file')
        self.assertEqual(set(self.git(self.remote, 'ls-tree', '-r', '--name-only', 'master').splitlines()),
                         {'dot_example', 'dot_new', 'tools/dots.py', 'tools/deploy.py'})
        self.assertEqual(self.git(self.remote, 'log', '-1', '--format=%s'), 'test: publish source')
        self.assertEqual(self.git(self.source, 'rev-parse', 'HEAD'),
                         self.git(self.remote, 'rev-parse', 'master'))
        self.assertEqual(self.git(self.source, 'status', '--porcelain'), '')
        self.assertEqual((self.home / '.example').read_bytes(), b'private live config\n')
        self.assertFalse(self.apply_log.exists())

    def test_sync_fast_forwards_and_requests_apply(self):
        tip = self.publish_update()
        self.cli('sync')
        self.assertEqual(self.git(self.source, 'rev-parse', 'HEAD'), tip)
        self.assertEqual((self.source / 'dot_example').read_bytes(), b'published config\n')
        self.assertEqual(self.git(self.source, 'status', '--porcelain'), '')
        self.assert_applied()

    def test_sync_refuses_conflicting_dirty_source_preserving_staging_and_bytes(self):
        self.publish_update()
        (self.source / 'dot_example').write_bytes(b'staged local config\n')
        self.git(self.source, 'add', 'dot_example')
        (self.source / 'dot_example').write_bytes(b'unstaged local config\x00\xff\n')
        (self.source / 'untracked').write_bytes(b'keep this too\n')
        self.assert_refuses_without_changes('sync', 'Unpublished source changes')

    def test_matching_dirty_bootstrap_adopts_remote_and_backs_up_metadata(self):
        tip = self.publish_update()
        (self.source / 'dot_example').write_bytes(b'published config\n')
        self.assert_bootstrap_adoption(tip)

    def test_matching_unborn_bootstrap_adopts_remote_and_backs_up_metadata(self):
        tip = self.git(self.remote, 'rev-parse', 'master')
        # Model an initial SSH-machine setup: files exist but no local commit.
        # Transport remains file-only; no SSH process or network is involved.
        shutil.rmtree(self.source / '.git')
        self.git(self.source, 'init', '--initial-branch=master')
        self.git(self.source, 'remote', 'add', 'origin', str(self.remote))
        self.git(self.source, 'add', 'dot_example')
        self.assert_bootstrap_adoption(tip)

    def assert_bootstrap_adoption(self, tip):
        files = self.source_bytes()
        metadata = {name: (self.source / '.git' / name).read_bytes()
                    for name in ('HEAD', 'config', 'index')}
        output = self.cli('sync')
        self.assertEqual(self.source_bytes(), files)
        self.assertEqual(self.git(self.source, 'rev-parse', 'HEAD'), tip)
        self.assertEqual(self.git(self.source, 'status', '--porcelain'), '')
        self.assertEqual(self.git(self.source, 'rev-parse', '--abbrev-ref', '@{upstream}'),
                         'origin/master')
        backups = list((self.home / '.local/state/dotsync-bootstrap-backups').iterdir())
        self.assertEqual(len(backups), 1)
        self.assertIn(str(backups[0]), output)
        for name, contents in metadata.items():
            self.assertEqual((backups[0] / 'git' / name).read_bytes(), contents)
        self.assert_applied()

    def test_sync_refuses_local_ahead_history(self):
        (self.source / 'dot_example').write_bytes(b'local commit\n')
        self.commit(self.source, 'local only')
        self.assert_refuses_without_changes('sync', 'ahead of or diverge')

    def test_sync_refuses_diverged_history(self):
        (self.source / 'dot_example').write_bytes(b'local commit\n')
        self.commit(self.source, 'local only')
        self.publish_update()
        self.assert_refuses_without_changes('sync', 'ahead of or diverge')

    def test_matching_dirty_tree_does_not_discard_diverged_history(self):
        (self.source / 'dot_example').write_bytes(b'local commit\n')
        self.commit(self.source, 'local only')
        self.publish_update()
        (self.source / 'dot_example').write_bytes(b'published config\n')
        self.assert_refuses_without_changes('sync', 'Local history diverges')

    def test_push_refuses_incoming_updates_without_committing_local_changes(self):
        self.publish_update()
        (self.source / 'dot_example').write_bytes(b'pending local edit\n')
        self.assert_refuses_without_changes('push', 'changes missing locally')


if __name__ == '__main__':
    unittest.main()
