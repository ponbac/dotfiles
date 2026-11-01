"""Exercise the migration CLI with isolated package/privilege command doubles."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]
SCRIPT = SOURCE / 'private_dot_local/bin/executable_desktop-package-migrate'
LEGACY = 'slack-desktop-wayland\ntelegram-desktop-bin\n'
FAKE = '''#!/usr/bin/env python3
import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
state = pathlib.Path(os.environ['PACKAGE_STATE'])
if name == 'hostname':
    print(os.environ.get('MIGRATION_HOST', 'omarchy'))
elif name == 'pgrep':
    sys.exit(int(os.environ.get('APP_RUNNING', '1')))
elif name == 'pacman':
    if sys.argv[1:] == ['-Qq']:
        print(state.read_text(), end='')
    elif sys.argv[1:] == ['-Qu']:
        updates = os.environ.get('PENDING_UPDATES', '')
        print(updates, end='')
        sys.exit(0 if updates else 1)
    elif sys.argv[1] == '-Q':
        print(sys.argv[2], '1.0-1')
    else:
        sys.exit(9)
elif name == 'pkexec':
    with open(os.environ['PRIVILEGE_LOG'], 'a') as stream:
        stream.write(json.dumps(sys.argv[1:]) + '\\n')
    if os.environ.get('TRANSACTION_FAIL'):
        sys.exit(1)
    packages = state.read_text().splitlines()
    for target in sys.argv[1:]:
        if target == 'omarchy/slack-desktop':
            packages.remove('slack-desktop-wayland')
            packages.append('slack-desktop')
        elif target == 'extra/telegram-desktop':
            packages.remove('telegram-desktop-bin')
            packages.append('telegram-desktop')
    state.write_text('\\n'.join(packages) + '\\n')
'''


class DesktopPackageMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.state = root / 'packages'
        self.state.write_text(LEGACY)
        self.log = root / 'privilege-log'
        binary = root / 'command-double'
        binary.write_text(FAKE)
        binary.chmod(0o755)
        for name in ('hostname', 'pacman', 'pgrep', 'pkexec'):
            (root / name).symlink_to(binary)
        self.env = dict(os.environ, PATH=str(root) + ':' + os.environ['PATH'],
                        PACKAGE_STATE=str(self.state), PRIVILEGE_LOG=str(self.log))

    def run_cli(self, *args, **env):
        return subprocess.run(['bash', str(SCRIPT), *args], env=dict(self.env, **env),
                              input='', text=True, capture_output=True)

    def test_preview_never_changes_packages_or_requests_privilege(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('omarchy/slack-desktop', result.stdout)
        self.assertIn('extra/telegram-desktop', result.stdout)
        self.assertEqual(self.state.read_text(), LEGACY)
        self.assertFalse(self.log.exists())

    def test_apply_uses_one_transaction_and_repeat_is_noop(self):
        result = self.run_cli('--apply', MIGRATION_HOST='omarchy-laptop')
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(calls, [['/usr/bin/pacman', '-S', '--needed', '--noconfirm',
                                 '--ask=4', 'omarchy/slack-desktop', 'extra/telegram-desktop']])
        self.assertEqual(set(self.state.read_text().splitlines()),
                         {'slack-desktop', 'telegram-desktop'})
        self.assertEqual(self.run_cli('--apply').returncode, 0)
        self.assertEqual(len(self.log.read_text().splitlines()), 1)

    def test_apply_does_not_install_an_absent_app(self):
        self.state.write_text('telegram-desktop-bin\nunrelated\n')
        result = self.run_cli('--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(self.state.read_text().splitlines()),
                         {'telegram-desktop', 'unrelated'})
        self.assertNotIn('omarchy/slack-desktop', self.log.read_text())

    def test_unsafe_conditions_refuse_before_privilege(self):
        for env, message in (({'MIGRATION_HOST': 'dev-1'}, 'supported'),
                             ({'MIGRATION_HOST': 'unknown-host'}, 'supported'),
                             ({'APP_RUNNING': '0'}, 'Quit Slack'),
                             ({'PENDING_UPDATES': 'glibc 1 -> 2\n'}, 'Pending system')):
            with self.subTest(env=env):
                result = self.run_cli('--apply', **env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertFalse(self.log.exists())
                self.assertEqual(self.state.read_text(), LEGACY)

    def test_failed_transaction_does_not_remove_old_apps_first(self):
        result = self.run_cli('--apply', TRANSACTION_FAIL='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.state.read_text(), LEGACY)
        self.assertEqual(len(self.log.read_text().splitlines()), 1)

    def test_chezmoi_only_manages_command_on_desktops(self):
        for host in ('omarchy', 'omarchy-laptop', 'dev-1', 'unknown-host'):
            with self.subTest(host=host):
                managed = subprocess.check_output([
                    'chezmoi', '--source', str(SOURCE), '--override-data',
                    json.dumps({'chezmoi': {'hostname': host}}),
                    'managed', '--include=files'], text=True).splitlines()
                self.assertEqual('.local/bin/desktop-package-migrate' in managed,
                                 host in ('omarchy', 'omarchy-laptop'))


if __name__ == '__main__':
    unittest.main()
