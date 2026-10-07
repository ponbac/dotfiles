"""Updater contracts through main(), isolated HOME and mocked external I/O.

Run: python3 -B -m unittest discover -s tools -p 'test_t3code_nightly_update.py' -v
No network, installed applications, package managers, or production state.
"""
import contextlib
import fcntl
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'private_dot_local/bin/executable_t3code-nightly-update'
LOADER = importlib.machinery.SourceFileLoader('t3code_nightly_update', str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
UPDATER = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(UPDATER)

OLD = '0.0.46-nightly.20261007.2774'
NEW = '0.0.47-nightly.20261008.100'
PAYLOAD = b'AppImage fixture bytes, never executable in tests'
SHA256 = hashlib.sha256(PAYLOAD).hexdigest()
SUBPROCESS_RUN = subprocess.run


def release(version=NEW, arch='x86_64'):
    name = f'T3-Code-{version}-{arch}.AppImage'
    return {'tag_name': f'v{version}', 'draft': False, 'prerelease': True,
            'assets': [{'name': name, 'size': len(PAYLOAD), 'digest': f'sha256:{SHA256}',
                        'browser_download_url':
                        f'https://github.com/pingdotgg/t3code/releases/download/v{version}/{name}'}]}


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='t3code-updater-test-')
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.root = self.home / '.local/share/t3code-nightly'
        self.enterContext(patch.dict(os.environ, {'HOME': str(self.home)}))
        self.enterContext(patch.object(UPDATER.socket, 'gethostname', return_value='omarchy'))
        self.enterContext(patch.object(UPDATER.platform, 'machine', return_value='x86_64'))
        self.pages = [[release()]]
        self.download = PAYLOAD
        self.download_exit = 0
        self.metadata_body = None
        self.metadata_exit = 0
        self.downloads = []
        self.api_calls = []
        self.curl_calls = []
        self.enterContext(patch.object(UPDATER.subprocess, 'run', side_effect=self.network))

    def network(self, command, **kwargs):
        # Emulate only external curl I/O, never staging, verification or promotion.
        self.curl_calls.append((command, kwargs))
        self.assertIsInstance(command, list)
        self.assertEqual(command[0], 'curl')
        self.assertEqual(command[-2], '--url')
        self.assertNotIn('shell', kwargs)
        url = command[-1]
        if url.startswith('https://api.github.com/repos/pingdotgg/t3code/releases'):
            self.api_calls.append(url)
            if '/tags/' in url:
                tag = url.rsplit('/', 1)[1]
                data = next((item for page in self.pages for item in page
                             if item.get('tag_name') == tag), {})
            else:
                page = int(url.rsplit('=', 1)[1])
                data = self.pages[page - 1] if page <= len(self.pages) else []
            body = self.metadata_body if self.metadata_body is not None else json.dumps(data).encode()
            return subprocess.CompletedProcess(command, self.metadata_exit, stdout=body)
        self.assertTrue(url.startswith('https://github.com/pingdotgg/t3code/releases/download/'), url)
        self.downloads.append(url)
        Path(command[command.index('--output') + 1]).write_bytes(self.download)
        return subprocess.CompletedProcess(command, self.download_exit)

    def cli(self, *args, succeeds=True):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = UPDATER.main(list(args))
        self.assertEqual(code, 0 if succeeds else 1, output.getvalue())
        return output.getvalue()

    def image(self, version, arch='x86_64'):
        return self.root / 'versions' / version / f'T3-Code-{version}-{arch}.AppImage'

    def stage_old(self):
        self.pages = [[release(OLD)]]
        self.cli('--release', OLD)
        self.pages = [[release()]]
        self.downloads.clear()
        return self.image(OLD)

    def assert_old_preserved(self, old):
        self.assertEqual((self.root / 'current.AppImage').resolve(), old)
        self.assertEqual(old.read_bytes(), PAYLOAD)
        self.assertFalse(self.image(NEW).exists())
        self.assertEqual(list(self.root.rglob('.download-*')), [])
        self.assertEqual(list(self.root.glob('.current-*')), [])

    def test_selection_paginates_and_orders_semver_then_numeric_nightly(self):
        wrong_tags = ['v99.0.0', 'v99.0.0-preview.20261009.1',
                      'v99.0.0-pr.7', 'nightly', 'v99.0.0-nightly.20261009.1-extra']
        wrong = [dict(release(), tag_name=tag) for tag in wrong_tags]
        wrong.append(dict(release('99.0.0-nightly.20261009.1'), draft=True))
        first = [release(OLD)] + wrong
        first += [dict(release(), tag_name='v1.0.0')] * (100 - len(first))
        self.pages = [first, [release('0.0.47-nightly.20261008.99'), release(),
                              release('0.0.46-nightly.20261231.9999')]]
        output = self.cli('--check')
        self.assertIn(NEW, output)
        self.assertIn('no download or local changes', output)
        self.assertEqual(len(self.api_calls), 2)
        self.assertEqual(self.downloads, [])
        self.assertEqual(list(self.home.iterdir()), [])

    def test_discovery_has_a_page_bound(self):
        self.pages = [[dict(release(), tag_name='v1.0.0')] * 100] * 20
        self.assertIn('No matching', self.cli('--check', succeeds=False))
        self.assertEqual(len(self.api_calls), 10)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_exact_release_stages_requested_version_not_latest(self):
        self.pages = [[release(), release(OLD)]]
        self.cli('--release', OLD)
        self.assertEqual(self.api_calls, [f'{UPDATER.API}/tags/v{OLD}'])
        self.assertEqual((self.root / 'current.AppImage').resolve(), self.image(OLD))
        self.assertFalse(self.image(NEW).exists())
        self.assertIn(f'/v{OLD}/', self.downloads[0])

    def test_curl_transport_uses_safe_args_https_and_bounded_transfers(self):
        self.cli()
        self.assertEqual(len(self.curl_calls), 2)
        for (command, kwargs), max_time, max_size in zip(
                self.curl_calls, (60, 600), (16 * 1024 * 1024, len(PAYLOAD))):
            self.assertEqual(command[:2], ['curl', '--disable'])
            for flag in ('--fail', '--location', '--silent', '--show-error'):
                self.assertIn(flag, command)
            for flag, value in (('--connect-timeout', '10'), ('--retry', '2'),
                                ('--proto', '=https'), ('--proto-redir', '=https'),
                                ('--max-time', str(max_time)), ('--max-filesize', str(max_size))):
                self.assertEqual(command[command.index(flag) + 1], value)
            self.assertFalse(kwargs.get('shell', False))
            self.assertEqual(kwargs['stderr'], subprocess.DEVNULL)
            self.assertNotIn('--dump-header', command)
        metadata_command, metadata_options = self.curl_calls[0]
        self.assertEqual(metadata_command[-2:], ['--url', f'{UPDATER.API}?per_page=100&page=1'])
        self.assertEqual(metadata_options['stdout'], subprocess.PIPE)
        download_command, download_options = self.curl_calls[1]
        temporary = Path(download_command[download_command.index('--output') + 1])
        self.assertEqual(temporary.parent, self.image(NEW).parent)
        self.assertTrue(temporary.name.startswith('.download-'))
        self.assertFalse(temporary.exists())
        self.assertEqual(download_options['stdout'], subprocess.DEVNULL)

    def test_bad_metadata_leaves_prior_image_and_never_downloads(self):
        old = self.stage_old()
        cases = [('http-error', json.dumps([release()]).encode(), 22, 'curl transfer failed'),
                 ('timeout', b'', 28, 'curl transfer failed'),
                 ('size-limit', b'', 63, 'curl transfer failed'),
                 ('oversized-body', b' ' * (16 * 1024 * 1024 + 1), 0, 'too large'),
                 ('malformed-json', b'{', 0, 'Expecting'),
                 ('not-a-list', b'{}', 0, 'release list')]
        for name, body, exit_code, diagnostic in cases:
            with self.subTest(name=name):
                self.metadata_body, self.metadata_exit = body, exit_code
                self.assertIn(diagnostic, self.cli(succeeds=False))
                self.assertEqual(self.downloads, [])
                self.assert_old_preserved(old)

    def test_exact_tag_response_must_match_and_never_falls_back_to_listing(self):
        for item in ({}, [], release(OLD), dict(release(), draft=True)):
            with self.subTest(item=item):
                self.api_calls.clear()
                self.metadata_body = json.dumps(item).encode()
                self.assertIn('exact non-draft', self.cli('--check', '--release', NEW, succeeds=False))
                self.assertEqual(self.api_calls, [f'{UPDATER.API}/tags/v{NEW}'])
                self.assertEqual(self.downloads, [])
                self.assertEqual(list(self.home.iterdir()), [])
        self.metadata_exit = 22
        self.api_calls.clear()
        self.assertIn('curl transfer failed', self.cli('--check', '--release', NEW, succeeds=False))
        self.assertEqual(self.api_calls, [f'{UPDATER.API}/tags/v{NEW}'])

    def test_promotion_retains_previous_image_and_is_idempotent(self):
        old = self.stage_old()
        old_stat = old.stat()
        output = self.cli()
        new = self.image(NEW)
        new_stat = new.stat()
        self.assertIn(f'Downloaded nightly {NEW}', output)
        self.assertIn('ready for next launch. No active work interrupted', output)
        self.assertEqual((self.root / 'current.AppImage').resolve(), new)
        self.assertEqual(new.read_bytes(), PAYLOAD)
        self.assertEqual(new_stat.st_mode & 0o777, 0o555)
        self.assertEqual(old.stat().st_ino, old_stat.st_ino)
        self.assertEqual(old.read_bytes(), PAYLOAD)
        self.assertIn('Already staged', self.cli())
        self.assertEqual(len(self.downloads), 1)
        self.assertEqual(new.stat().st_ino, new_stat.st_ino)
        self.assertEqual(new.stat().st_mtime_ns, new_stat.st_mtime_ns)

    def test_arm64_uses_exact_arm64_asset(self):
        self.pages = [[release(arch='arm64')]]
        with patch.object(UPDATER.platform, 'machine', return_value='aarch64'), \
             patch.object(UPDATER.socket, 'gethostname', return_value='omarchy-laptop'):
            self.cli()
        self.assertEqual((self.root / 'current.AppImage').resolve(), self.image(NEW, 'arm64'))
        self.assertTrue(self.downloads[0].endswith('-arm64.AppImage'))

    def test_bad_downloads_leave_prior_current_and_no_partial_image(self):
        old = self.stage_old()
        cases = [
            ('checksum', b'x' * len(PAYLOAD), 0, 'SHA256'),
            ('short', PAYLOAD[:-1], 0, 'Partial download'),
            ('oversized', PAYLOAD + b'x', 0, 'exceeds asset size'),
            ('interrupted', PAYLOAD[:5], 18, 'curl transfer failed'),
            ('timeout', PAYLOAD[:5], 28, 'curl transfer failed'),
            ('oversize-limit', PAYLOAD[:5], 63, 'curl transfer failed'),
            ('http-error-with-complete-bytes', PAYLOAD, 22, 'curl transfer failed'),
        ]
        for name, data, exit_code, diagnostic in cases:
            with self.subTest(name=name):
                self.download, self.download_exit = data, exit_code
                self.assertIn(diagnostic, self.cli(succeeds=False))
                self.assert_old_preserved(old)

    def test_untrusted_metadata_is_rejected_before_download(self):
        old = self.stage_old()
        valid_url = release()['assets'][0]['browser_download_url']
        cases = [('browser_download_url', 'https://evil.invalid/image'),
                 ('browser_download_url', valid_url.replace('/pingdotgg/', '/attacker/')),
                 ('browser_download_url', valid_url.replace(f'/v{NEW}/', f'/v{OLD}/')),
                 ('browser_download_url', valid_url + '?redirect=evil'),
                 ('digest', None), ('digest', 'sha256:bad'),
                 ('size', 0), ('size', 1024 ** 3 + 1), ('size', True),
                 ('name', f'T3-Code-{NEW}-arm64.AppImage')]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                item = release()
                item['assets'][0][key] = value
                self.pages = [[item]]
                self.cli(succeeds=False)
                self.assertEqual(self.downloads, [])
                self.assert_old_preserved(old)

    def test_existing_different_version_bytes_are_never_overwritten(self):
        old = self.stage_old()
        image = self.image(NEW)
        image.parent.mkdir(parents=True)
        image.write_bytes(b'local differing file')
        self.assertIn('refusing to overwrite', self.cli(succeeds=False))
        self.assertEqual(image.read_bytes(), b'local differing file')
        self.assertEqual((self.root / 'current.AppImage').resolve(), old)
        self.assertEqual(self.downloads, [])

    def test_older_release_is_never_promoted_even_when_explicit(self):
        self.cli()
        self.pages = [[release(OLD)]]
        self.downloads.clear()
        for args in [(), ('--check',), ('--release', OLD)]:
            with self.subTest(args=args):
                self.assertIn('Refusing downgrade', self.cli(*args, succeeds=False))
                self.assertEqual((self.root / 'current.AppImage').resolve(), self.image(NEW))
                self.assertEqual(self.downloads, [])

    def test_status_is_offline_read_only_and_reports_metadata(self):
        self.assertIn('No nightly staged', self.cli('--status'))
        self.assertEqual(list(self.home.iterdir()), [])
        self.cli()
        self.api_calls.clear()
        self.downloads.clear()
        before = self.image(NEW).stat()
        output = self.cli('--status')
        for value in (NEW, str(self.image(NEW)), SHA256, f'{len(PAYLOAD)} bytes'):
            self.assertIn(value, output)
        self.assertEqual(self.api_calls, [])
        self.assertEqual(self.downloads, [])
        self.assertEqual(self.image(NEW).stat().st_mtime_ns, before.st_mtime_ns)

    def test_lock_prevents_overlapping_update_before_network(self):
        self.root.mkdir(parents=True)
        with (self.root / '.update.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertIn('holds the lock', self.cli(succeeds=False))
        self.assertEqual(self.api_calls, [])
        self.assertFalse((self.root / 'current.AppImage').exists())

    def test_version_flag_is_an_offline_cli_without_side_effects(self):
        result = SUBPROCESS_RUN([sys.executable, '-B', str(SCRIPT), '--version'],
                                env={'HOME': str(self.home), 'PATH': os.defpath},
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('1.0.0', result.stdout)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_disallowed_hosts_and_architectures_refuse_before_io(self):
        for host in ('dev1', 'dev-1', 'unknown'):
            with self.subTest(host=host), \
                 patch.object(UPDATER.socket, 'gethostname', return_value=host):
                self.assertIn('Only omarchy', self.cli(succeeds=False))
        with patch.object(UPDATER.platform, 'machine', return_value='riscv64'):
            self.assertIn('Unsupported architecture', self.cli(succeeds=False))
        self.assertEqual(self.api_calls, [])
        self.assertEqual(list(self.home.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
