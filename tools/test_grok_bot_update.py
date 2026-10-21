"""Grok Bot updater contracts with disposable state and simulated external I/O.

Run: python3 -B -m unittest discover -s tools -p 'test_grok_bot_update.py' -v
Requires real Arch vercmp. Never downloads, builds, installs, or reads host profiles.
"""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'private_dot_local/bin/executable_grok-bot-update'
PACKAGING = ROOT / 'private_dot_local/share/grok-bot-packaging'
ASAR_SCRIPT = PACKAGING / 'extract-asar.py'
REAL_RUN = subprocess.run
REAL_ITERDIR = Path.iterdir
VERSION = '0.3.2'
COMMIT = '0123456789abcdef0123456789abcdef01234567'
PACKAGE_BYTES = b'inert local package fixture; never installed'


def manifest(version=VERSION, commit=COMMIT):
    return {
        'version': version,
        'commitSha': commit,
        'debUrl': (f'https://downloads.cursor.com/grokbot/stable/{commit}/'
                   f'linux/x64/grok-bot_{version}_amd64.deb'),
    }


def snapshot(root):
    """Observe file bytes and write timestamps, ignoring read access times."""
    return {
        path.relative_to(root).as_posix(): (
            path.stat().st_mode, path.stat().st_mtime_ns,
            path.read_bytes() if path.is_file() else None,
        )
        for path in [root, *root.rglob('*')]
    }


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='grok-bot-update-test-')
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.enterContext(patch.dict(os.environ, {
            'HOME': str(self.home),
            'XDG_CONFIG_HOME': str(self.home / '.config'),
            'XDG_CACHE_HOME': str(self.home / '.cache'),
            'XDG_STATE_HOME': str(self.home / '.local/state'),
        }))
        # Load after isolating HOME: module-level cache/recipe paths must never
        # point at the user's installed updater state, even during import.
        loader = importlib.machinery.SourceFileLoader('grok_bot_update_test_owner', str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.updater = importlib.util.module_from_spec(spec)
        loader.exec_module(self.updater)
        self.cache = self.home / '.cache/grok-bot-update'
        self.packaging = self.home / '.local/share/grok-bot-packaging'
        shutil.copytree(PACKAGING, self.packaging)
        self.vercmp = shutil.which('vercmp')
        self.assertIsNotNone(self.vercmp, 'These contracts require real Arch vercmp')
        self.enterContext(patch.object(self.updater.socket, 'gethostname', return_value='omarchy'))
        self.enterContext(patch.object(self.updater.platform, 'machine', return_value='x86_64'))
        self.enterContext(patch.object(self.updater.os, 'geteuid', return_value=1000))
        self.current = '0.3.1-1'
        self.metadata = manifest()
        self.calls = []
        self.processes = []

        def process_inventory(path):
            if path == Path('/proc'):
                return iter(self.processes)
            return REAL_ITERDIR(path)

        self.enterContext(patch.object(Path, 'iterdir', process_inventory))
        self.enterContext(patch.object(self.updater.subprocess, 'run', side_effect=self.external))

    def external(self, command, **kwargs):
        """Only vercmp runs for real; every other subprocess is fail-closed."""
        self.calls.append(list(command))
        program = command[0]
        if program == 'vercmp':
            return REAL_RUN([self.vercmp, *command[1:]], **{**kwargs, 'timeout': 10})
        if command == ['pacman', '-Q', 'grok-bot-bin']:
            return subprocess.CompletedProcess(command, 0, stdout=f'grok-bot-bin {self.current}\n')
        if program == 'curl':
            url = command[command.index('--url') + 1]
            if '--output' in command:
                self.assertEqual(url, manifest()['debUrl'])
                Path(command[command.index('--output') + 1]).write_bytes(b'inert deb fixture')
                return subprocess.CompletedProcess(command, 0, stdout=b'')
            self.assertEqual(url, 'https://api2.cursor.sh/updates/api/download/stable/linux-x64/sand')
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(self.metadata).encode())
        if program == 'makepkg':
            # Simulate the external builder's output, not the updater's receipt,
            # verification, cache publication, or subsequent reuse decisions.
            output = Path(kwargs['env']['PKGDEST'])
            self.assertTrue(output.is_relative_to(self.home))
            (output / f'grok-bot-bin-{VERSION}-1-x86_64.pkg.tar.zst').write_bytes(PACKAGE_BYTES)
            return subprocess.CompletedProcess(command, 0)
        if command[:2] == ['pacman', '-Qp']:
            self.assertEqual(Path(command[2]).read_bytes(), PACKAGE_BYTES)
            return subprocess.CompletedProcess(command, 0, stdout=f'grok-bot-bin {VERSION}-1\n')
        if program in ('sudo', 'pkexec', 'notify-send'):
            return subprocess.CompletedProcess(command, 0)
        self.fail(f'Unexpected external command (not executed): {command!r}')

    def cli(self, *args):
        output = io.StringIO()
        with patch.object(sys, 'argv', [str(SCRIPT), *args]), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.updater.main()
        return output.getvalue()

    def assert_no_build_download_or_elevation(self):
        self.assertFalse(any(command[0] in ('makepkg', 'sudo', 'pkexec') or
                             (command[0] == 'curl' and '--output' in command)
                             for command in self.calls), self.calls)

    def staged_package(self):
        packages = list(self.cache.glob('packages/*/*.pkg.tar.zst'))
        self.assertEqual(len(packages), 1)
        return packages[0]

    def test_official_stable_metadata_is_accepted(self):
        output = self.cli('--check')
        self.assertIn(VERSION, output)
        self.assertIn('Update available', output)
        self.assert_no_build_download_or_elevation()
        self.assertFalse(self.cache.exists())

    def test_untrusted_metadata_is_rejected_before_package_io(self):
        good_url = manifest()['debUrl']
        cases = [
            ('wrong host', dict(manifest(), debUrl=good_url.replace('downloads.cursor.com', 'evil.invalid')), 'URL'),
            ('wrong path', dict(manifest(), debUrl=good_url.replace('/grokbot/stable/', '/cursor/stable/')), 'URL'),
            ('wrong architecture', dict(manifest(), debUrl=good_url.replace('/linux/x64/', '/linux/arm64/')), 'URL'),
            ('query suffix', dict(manifest(), debUrl=good_url + '?redirect=evil'), 'URL'),
            ('shell injection', manifest('0.3.2; touch OWNED'), 'version'),
            ('newline injection', manifest('0.3.2\n$(touch OWNED)'), 'version'),
            ('prerelease', manifest('0.3.2-beta.1'), 'version'),
            ('short commit', manifest(commit='abc123'), 'commit'),
            ('non-hex commit', manifest(commit='g' * 40), 'commit'),
            ('non-string commit', manifest(commit=None), 'commit'),
            ('not an object', [], 'manifest'),
        ]
        before = snapshot(self.home)
        for label, metadata, diagnostic in cases:
            with self.subTest(case=label):
                self.metadata = metadata
                self.calls.clear()
                with self.assertRaisesRegex(self.updater.UpdateError, diagnostic):
                    self.cli()
                self.assert_no_build_download_or_elevation()
                self.assertEqual(snapshot(self.home), before)

    def test_no_downgrade_including_arch_pkgrel_and_epoch(self):
        # Real vercmp must distinguish pkgrel and epoch, not just split semver.
        for current in ('0.4.0-1', '0.3.2-1', '0.3.2-2', '1:0.2.0-1'):
            for args in (('--check',), (), ('--install',)):
                with self.subTest(current=current, args=args):
                    self.current = current
                    self.calls.clear()
                    self.assertIn('no downgrade', self.cli(*args))
                    self.assert_no_build_download_or_elevation()
                    self.assertEqual(list(self.cache.glob('packages/*')), [])

    def test_version_rechecked_after_lock_prevents_stale_upgrade(self):
        original_external = self.external
        queries = []

        def package_updated_during_check(command, **kwargs):
            if command == ['pacman', '-Q', 'grok-bot-bin']:
                queries.append(command)
                self.current = '0.3.1-1' if len(queries) == 1 else '0.3.2-2'
            return original_external(command, **kwargs)

        with patch.object(self.updater.subprocess, 'run', side_effect=package_updated_during_check):
            self.assertIn('no downgrade', self.cli('--install'))
        self.assert_no_build_download_or_elevation()
        self.assertEqual(list(self.cache.glob('packages/*')), [])

    def test_version_rechecked_after_staging_prevents_downgrade(self):
        original_external = self.external

        def package_updated_during_build(command, **kwargs):
            result = original_external(command, **kwargs)
            if command[0] == 'makepkg':
                self.current = '0.3.2-2'
            return result

        with patch.object(self.updater.subprocess, 'run', side_effect=package_updated_during_build):
            self.assertIn('no downgrade', self.cli('--install'))
        self.assertFalse(any(command[0] in ('sudo', 'pkexec') for command in self.calls))
        self.assertEqual(self.staged_package().read_bytes(), PACKAGE_BYTES)

    def test_failed_notification_is_retried_without_rebuilding(self):
        original_external = self.external

        def failed_notification(command, **kwargs):
            if command[0] == 'notify-send':
                self.calls.append(list(command))
                return subprocess.CompletedProcess(command, 1)
            return original_external(command, **kwargs)

        with patch.object(self.updater.shutil, 'which', return_value='/usr/bin/notify-send'):
            with patch.object(self.updater.subprocess, 'run', side_effect=failed_notification):
                self.cli()
            self.calls.clear()
            self.cli()
            self.assert_no_build_download_or_elevation()
            self.assertTrue(any(command[0] == 'notify-send' for command in self.calls))
            self.calls.clear()
            self.cli()
            self.assertFalse(any(command[0] == 'notify-send' for command in self.calls))

    def test_check_and_status_are_read_only_with_empty_and_populated_cache(self):
        for populated in (False, True):
            if populated:
                self.cli()
                self.assertEqual(self.staged_package().read_bytes(), PACKAGE_BYTES)
            for mode in ('--check', '--status'):
                with self.subTest(populated=populated, mode=mode):
                    before = snapshot(self.home)
                    self.calls.clear()
                    output = self.cli(mode)
                    self.assertIn(self.current, output)
                    if mode == '--check':
                        self.assertIn('Update available', output)
                        self.assertTrue(any(command[0] == 'curl' for command in self.calls))
                    else:
                        self.assertFalse(any(command[0] == 'curl' for command in self.calls))
                        if populated:
                            self.assertIn(str(self.staged_package().parent), output)
                    self.assert_no_build_download_or_elevation()
                    self.assertEqual(snapshot(self.home), before)

    def test_install_refuses_live_app_but_accepts_closed_app(self):
        self.cli()
        package = self.staged_package()
        # Substitute only the external process inventory. No actual host process
        # inspection, app launch, or mocked updater app-running predicate.
        proc = self.home / 'processes/123'
        proc.mkdir(parents=True)
        (proc / 'exe').symlink_to('/opt/Grok Bot/grok-bot')
        self.processes.append(proc)
        self.calls.clear()
        with self.assertRaisesRegex(self.updater.UpdateError, 'Quit Grok Bot'):
            self.cli('--install')
        self.assert_no_build_download_or_elevation()
        self.assertEqual(package.read_bytes(), PACKAGE_BYTES)
        self.processes.clear()
        self.cli('--install')
        installs = [command for command in self.calls if command[0] in ('sudo', 'pkexec')]
        self.assertEqual(len(installs), 1)
        self.assertEqual(installs[0][1:], ['/usr/bin/pacman', '-U', '--noconfirm', str(package)])

    def test_corrupt_cached_package_is_not_reused_or_elevated(self):
        self.cli()
        package = self.staged_package()
        # Positive reuse control: an intact cache does not need a new download
        # or build. Its receipt was produced by the updater, not by this fixture.
        self.calls.clear()
        self.cli()
        self.assert_no_build_download_or_elevation()
        package.write_bytes(b'corrupted package bytes')
        before = snapshot(package.parent)
        self.calls.clear()
        with self.assertRaisesRegex(self.updater.UpdateError, 'Cached package changed'):
            self.cli('--install')
        self.assert_no_build_download_or_elevation()
        self.assertEqual(snapshot(package.parent), before)


class AsarInjectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='grok-bot-asar-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.archive = self.root / 'app.asar'
        self.unpacked = self.root / 'app.asar.unpacked'
        native = self.unpacked / 'native/addon.node'
        native.parent.mkdir(parents=True)
        native.write_bytes(b'\x7fELF\x00unpacked fixture')
        self.tray = self.root / 'linux-tray.cjs'
        self.tray.write_bytes(b"require('./main.cjs'); // tray fixture\n")

    def fixture(self, main='dist/electron-main/main.cjs', include_main=True):
        # Independently encode Electron's pickle header; never use the owner's
        # pack/extract helpers to construct or verify their own test inputs.
        packed = {
            'package.json': json.dumps({'name': 'fixture', 'main': main, 'custom': {'keep': True}}).encode(),
            'assets/unrelated.bin': b'\x00\xffuntouched\x00',
            'assets/empty.txt': b'',
            'bin/helper': b'#!/bin/sh\nexit 0\n',
        }
        if include_main:
            packed['dist/electron-main/main.cjs'] = b'// original main process\n'
        header = {'files': {}}
        offset = 0
        for name, data in packed.items():
            node = header
            parts = name.split('/')
            for part in parts[:-1]:
                node = node['files'].setdefault(part, {'files': {}})
            node['files'][parts[-1]] = {'offset': str(offset), 'size': len(data)}
            if name == 'bin/helper':
                node['files'][parts[-1]]['executable'] = True
            offset += len(data)
        header['files']['native'] = {'files': {'addon.node': {
            'size': len((self.unpacked / 'native/addon.node').read_bytes()), 'unpacked': True,
        }}}
        payload = json.dumps(header, separators=(',', ':')).encode()
        padding = b'\0' * (-len(payload) % 4)
        header_size = 8 + len(payload) + len(padding)
        self.archive.write_bytes(struct.pack('<IIII', 4, header_size, header_size - 4, len(payload)) +
                                 payload + padding + b''.join(packed.values()))
        return packed

    def members(self):
        blob = self.archive.read_bytes()
        _, header_size, _, json_size = struct.unpack_from('<IIII', blob)
        header = json.loads(blob[16:16 + json_size])
        packed, unpacked = {}, set()

        def walk(node, prefix=''):
            for name, child in node['files'].items():
                path = prefix + name
                if 'files' in child:
                    walk(child, path + '/')
                elif child.get('unpacked'):
                    unpacked.add(path)
                else:
                    start = 8 + header_size + int(child['offset'])
                    packed[path] = blob[start:start + child['size']]
        walk(header)
        return packed, unpacked

    def inject(self):
        return REAL_RUN(
            [sys.executable, '-B', str(ASAR_SCRIPT), 'inject-tray', str(self.archive),
             str(self.unpacked), str(self.tray)],
            env={'HOME': str(self.root), 'PATH': os.defpath, 'TMPDIR': str(self.root)},
            capture_output=True, text=True, timeout=10,
        )

    def test_injection_rewrites_entrypoint_and_preserves_other_members(self):
        original = self.fixture()
        unpacked_before = snapshot(self.unpacked)
        result = self.inject()
        self.assertEqual(result.returncode, 0, result.stderr)
        packed, unpacked = self.members()
        package = json.loads(packed.pop('package.json'))
        original.pop('package.json')
        self.assertEqual(package, {'name': 'fixture', 'main': 'dist/electron-main/linux-tray.cjs',
                                   'custom': {'keep': True}})
        self.assertEqual(packed.pop('dist/electron-main/linux-tray.cjs'), self.tray.read_bytes())
        self.assertEqual(packed, original)
        self.assertEqual(unpacked, {'native/addon.node'})
        blob = self.archive.read_bytes()
        json_size = struct.unpack_from('<I', blob, 12)[0]
        header = json.loads(blob[16:16 + json_size])
        self.assertTrue(header['files']['bin']['files']['helper'].get('executable'))
        self.assertEqual(snapshot(self.unpacked), unpacked_before)

    def test_changed_or_missing_expected_entrypoint_leaves_archive_unchanged(self):
        for main, include_main, diagnostic in (
                ('dist/new-main.cjs', True, 'Upstream entrypoint changed'),
                ('dist/electron-main/main.cjs', False, 'Missing upstream main process')):
            with self.subTest(main=main, include_main=include_main):
                self.fixture(main, include_main)
                before = self.archive.read_bytes()
                unpacked_before = snapshot(self.unpacked)
                result = self.inject()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(diagnostic, result.stderr)
                self.assertEqual(self.archive.read_bytes(), before)
                self.assertEqual(snapshot(self.unpacked), unpacked_before)


if __name__ == '__main__':
    unittest.main()
