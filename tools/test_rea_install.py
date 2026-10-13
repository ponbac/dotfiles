"""Exercise the REA skill-only installer with an isolated HOME and no real CLI."""
import contextlib
import fcntl
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('install-rea-skills.py')
SPEC = importlib.util.spec_from_file_location('rea_install', SCRIPT)
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


class ReaInstallTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.home = Path(directory.name) / 'home'
        self.home.mkdir()
        environment = patch.dict(os.environ, {'HOME': str(self.home)}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.shared = self.home / '.agents/skills/reverse-engineer-anything'
        self.claude = self.home / '.claude/skills/reverse-engineer-anything'
        self.backups = self.home / '.local/state/rea-skill-install-backups'
        self.binary = Path(directory.name) / 'mise/bin/rea'
        self.command = [str(self.binary), 'setup', '--skill-client', 'shared',
                        '--skill-client', 'claude_code', '--yes', '--json']
        self.stdout = io.StringIO()

    def report(self, status='planned', actions=None, applied=None):
        if actions is None:
            actions = [
                {'id': 'install_skill', 'kind': 'install_skill', 'target': str(self.shared),
                 'external': False, 'operation': 'install'},
                {'id': 'install_skill:claude_code', 'kind': 'install_skill',
                 'target': str(self.claude), 'external': False, 'operation': 'install'},
            ]
        return subprocess.CompletedProcess([], 0, json.dumps({
            'status': status, 'plannedActions': actions,
            'appliedActions': [] if applied is None else applied,
            'clients': {}, 'doctor': {'private': 'SECRET'},
        }), 'PRIVATE STDERR')

    def invoke(self, effect):
        with patch('sys.argv', [str(SCRIPT), str(self.binary)]), \
             patch.object(INSTALLER.subprocess, 'run', side_effect=effect) as run, \
             contextlib.redirect_stdout(self.stdout):
            INSTALLER.main()
        return run

    def assert_locked(self):
        lock = self.home / '.local/state/agent-integration-update.lock'
        with lock.open('a') as handle:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_skill_only_setup_backs_up_before_writing_under_shared_lock(self):
        self.shared.mkdir(parents=True)
        (self.shared / 'SKILL.md').write_text('local changes')
        (self.shared / 'references').mkdir()
        (self.shared / 'references/local.md').write_text('local reference')
        config = self.home / '.claude.json'
        config.write_text('untouched configuration')

        def cli(command, **options):
            self.assert_locked()
            self.assertTrue(options['capture_output'])
            self.assertEqual(command[:len(self.command)], self.command)
            if '--dry-run' in command:
                self.assertFalse(self.backups.exists())
                return self.report()
            backup, = self.backups.iterdir()
            self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
            self.assertEqual(self.backups.stat().st_mode & 0o777, 0o700)
            self.assertEqual((backup / 'manifest.json').stat().st_mode & 0o777, 0o600)
            self.assertEqual((backup / '.agents/skills/reverse-engineer-anything/SKILL.md').read_text(),
                             'local changes')
            self.assertEqual((backup / '.agents/skills/reverse-engineer-anything/references/local.md').read_text(),
                             'local reference')
            self.assertEqual(json.loads((backup / 'manifest.json').read_text()), [
                {'path': '.agents/skills/reverse-engineer-anything', 'existed': True},
                {'path': '.claude/skills/reverse-engineer-anything', 'existed': False},
            ])
            (self.shared / 'SKILL.md').write_text('new shared skill')
            self.claude.mkdir(parents=True)
            (self.claude / 'SKILL.md').write_text('new Claude skill')
            return self.report('ready', applied=['installed_skill'])

        run = self.invoke(cli)
        self.assertEqual([call.args[0] for call in run.call_args_list],
                         [self.command + ['--dry-run'], self.command])
        self.assertEqual((self.shared / 'SKILL.md').read_text(), 'new shared skill')
        self.assertEqual(config.read_text(), 'untouched configuration')
        self.assertIn('REA skills: ready', self.stdout.getvalue())
        self.assertNotIn('SECRET', self.stdout.getvalue())
        self.assertNotIn('PRIVATE', self.stdout.getvalue())

    def test_noop_does_not_create_backup_or_apply(self):
        def cli(command, **options):
            self.assert_locked()
            return self.report(actions=[])

        run = self.invoke(cli)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0], self.command + ['--dry-run'])
        self.assertFalse(self.backups.exists())
        self.assertEqual(self.stdout.getvalue(), 'REA skills: unchanged\n')

    def test_unexpected_plan_never_backs_up_or_applies(self):
        for change in ({'kind': 'configure_client'}, {'kind': 'install_hopper'},
                       {'target': str(self.home / '.claude.json')},
                       {'target': []}, {'external': True}, {'operation': 'update'}):
            with self.subTest(change=change):
                report = json.loads(self.report().stdout)
                report['plannedActions'][0].update(change)
                response = subprocess.CompletedProcess([], 0, json.dumps(report), '')
                with self.assertRaisesRegex(SystemExit, 'unexpected action'):
                    self.invoke([response])
                self.assertFalse(self.backups.exists())

    def test_failure_and_confirmation_statuses_are_rejected(self):
        for status in ('needs_human', 'needs_confirmation', 'cancelled', 'failed', 'unknown'):
            with self.subTest(status=status):
                with self.assertRaisesRegex(SystemExit, 'unsuccessful status'):
                    self.invoke([self.report(status)])
                self.assertFalse(self.backups.exists())

    def test_apply_failure_preserves_recovery_backup_and_is_not_success(self):
        for response, message in (
            (self.report('needs_human'), 'unsuccessful status'),
            (self.report('needs_confirmation'), 'unsuccessful status'),
            (subprocess.CompletedProcess([], 7, 'SECRET', 'SECRET'), 'exit 7'),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(SystemExit, message) as raised:
                    self.invoke([self.report(), response])
                self.assertNotIn('SECRET', str(raised.exception))
                self.assertNotIn('REA skills: ready', self.stdout.getvalue())
        self.assertEqual(len(list(self.backups.iterdir())), 3)

    def test_invalid_json_and_nonzero_exit_never_apply(self):
        for response, message in (
            (subprocess.CompletedProcess([], 4, 'SECRET', 'SECRET'), 'exit 4'),
            (subprocess.CompletedProcess([], 0, 'not json SECRET', ''), 'invalid JSON'),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(SystemExit, message) as raised:
                    self.invoke([response])
                self.assertNotIn('SECRET', str(raised.exception))
                self.assertFalse(self.backups.exists())

    def test_symlink_skill_directory_ancestor_and_files_are_rejected(self):
        source = self.home.parent / 'source'
        source.mkdir()
        original = source / 'SKILL.md'
        original.write_text('source must not change')
        self.shared.mkdir(parents=True)
        for name in ('.agents', '.agents/skills', '.claude',
                     '.agents/skills/reverse-engineer-anything',
                     '.agents/skills/reverse-engineer-anything/SKILL.md',
                     '.agents/skills/reverse-engineer-anything/references',
                     '.agents/skills/reverse-engineer-anything/SKILL.md.rea.backup'):
            with self.subTest(path=name):
                path = self.home / name
                saved = path.with_name(path.name + '-saved')
                if path.exists():
                    path.rename(saved)
                target = original if path.name.startswith('SKILL.md') else source
                path.symlink_to(target)
                try:
                    with self.assertRaisesRegex(SystemExit, 'symlink path'):
                        self.invoke([])
                    self.assertFalse(self.backups.exists())
                    self.assertEqual(original.read_text(), 'source must not change')
                finally:
                    path.unlink()
                    if saved.exists():
                        saved.rename(path)

    def test_mise_installation_resolves_npm_and_aube_executables(self):
        for relative in ('bin/rea', 'node_modules/.bin/rea'):
            with self.subTest(layout=relative):
                prefix = self.home.parent / relative.split('/')[0]
                executable = prefix / relative
                executable.parent.mkdir(parents=True)
                executable.write_text('placeholder executable')
                self.binary = prefix
                run = self.invoke([self.report(actions=[])])
                self.assertEqual(run.call_args.args[0][0], str(executable))
                self.assertFalse(self.backups.exists())

    def test_missing_mise_executable_never_runs_setup(self):
        self.binary = self.home.parent / 'empty-installation'
        self.binary.mkdir()
        with self.assertRaisesRegex(SystemExit, 'executable missing'):
            self.invoke([])
        self.assertFalse(self.backups.exists())

    def test_relative_executable_is_rejected_without_running(self):
        self.binary = Path('rea')
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                self.invoke([])
        self.assertEqual(raised.exception.code, 2)
        self.assertFalse((self.home / '.local').exists())


if __name__ == '__main__':
    unittest.main()
