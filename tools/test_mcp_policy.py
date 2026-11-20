"""Render shared MCP policies without connecting servers or touching live config."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
import unittest

SOURCE = Path(__file__).resolve().parents[1]

POLICIES = (
    ('private_dot_pi/private_agent/modify_mcp.json', 'mcpServers'),
    ('modify_private_dot_claude.json', 'mcpServers'),
    ('private_dot_codex/modify_private_config.toml', 'mcp_servers'),
    ('private_dot_config/opencode/modify_opencode.json', 'mcp'),
    ('private_dot_gemini/private_config/modify_private_mcp_config.json', 'mcpServers'),
)


class MCPPolicyTests(unittest.TestCase):
    def setUp(self):
        # Never read the real host token: an empty HOME and no token in the environment.
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.home = Path(directory.name)
        self.token = None

    def render(self, path, current):
        template = (SOURCE / path).read_text()
        data = {'chezmoi': {'sourceDir': str(SOURCE), 'homeDir': str(self.home),
                            'stdin': current}}
        env = {k: v for k, v in os.environ.items() if k != 'EXECUTOR_MCP_TOKEN'}
        if self.token is not None:
            env['EXECUTOR_MCP_TOKEN'] = self.token
        output = subprocess.check_output(
            ['chezmoi', '--source', str(SOURCE), '--override-data', json.dumps(data),
             'execute-template', template], text=True, env=env,
        )
        return tomllib.loads(output) if path.endswith('.toml') else json.loads(output)

    def test_shared_servers_preserve_unrelated_settings_and_are_idempotent(self):
        for path, key in POLICIES:
            with self.subTest(path=path):
                if path.endswith('.toml'):
                    before = ('local_setting = "keep"\n'
                              '[mcp_servers.railway]\ncommand = "railway"\n'
                              '[mcp_servers.executor]\nurl = "https://wrong.invalid"\n'
                              'bearer_token = "host-secret"\n'
                              '[mcp_servers.rea]\ncommand = "wrong-rea"\n'
                              'args = ["update"]\n')
                else:
                    before = json.dumps({'local_setting': 'keep', key: {
                        'railway': {'command': ['railway', 'mcp']},
                        'playwriter': {'enabled': False},
                        'rea': {'command': 'wrong-rea', 'args': ['update']},
                        'executor': {'url': 'https://wrong.invalid',
                                     'headers': {'Authorization': 'host-secret'}},
                    }})
                self.token = 'env-token' if path.startswith('private_dot_gemini/') else None
                after = self.render(path, before)
                self.assertEqual(after['local_setting'], 'keep')
                # REA is installed but disabled: a stale live registration is removed.
                self.assertEqual(set(after[key]), {'executor'})
                if path.startswith('private_dot_gemini/'):
                    # Antigravity sends ${VAR} headers literally, so the token is written.
                    self.assertEqual(after[key]['executor'],
                                     {'url': 'https://executor.pike-quail.ts.net/mcp',
                                      'headers': {'Authorization': 'Bearer env-token'}})
                    self.assertNotIn('host-secret', json.dumps(after))
                    self.assertEqual(self.render(path, json.dumps(after)), after)
                    self.assertEqual(self.render(path, ''), {key: after[key]})
                    continue
                executor = after[key]['executor']
                self.assertEqual(executor['url'], 'https://executor.pike-quail.ts.net/mcp')
                self.assertNotIn('host-secret', json.dumps(after))
                if key == 'mcp_servers':
                    self.assertEqual(executor['bearer_token_env_var'], 'EXECUTOR_MCP_TOKEN')
                    self.assertEqual(executor['default_tools_approval_mode'], 'writes')
                    # These are the only top-level settings exercised by this fixture.
                    again = 'local_setting = "keep"\n' + '\n'.join(
                        f'[mcp_servers.{name}]\n' + '\n'.join(
                            f'{k} = {json.dumps(v)}' for k, v in server.items())
                        for name, server in after[key].items())
                else:
                    token = '{env:EXECUTOR_MCP_TOKEN}' if key == 'mcp' else '${EXECUTOR_MCP_TOKEN}'
                    self.assertEqual(executor['headers'], {'Authorization': f'Bearer {token}'})
                    if key == 'mcp':
                        self.assertEqual(executor['type'], 'remote')
                        self.assertIs(executor['oauth'], False)
                        self.assertIs(executor['enabled'], True)
                    again = json.dumps(after)
                # Codex's preferences are also installed when rendering the sparse fixture.
                self.assertEqual(self.render(path, again), after)
                self.assertEqual(self.render(path, '')[key], after[key])

    def test_antigravity_token_falls_back_to_env_file_then_live_header(self):
        path = 'private_dot_gemini/private_config/modify_private_mcp_config.json'
        headers = lambda out: out['mcpServers']['executor'].get('headers')
        live = json.dumps({'mcpServers': {'executor': {
            'url': 'https://executor.pike-quail.ts.net/mcp',
            'headers': {'Authorization': 'Bearer live-token'}}}})
        # No token anywhere: an existing header survives, and none is invented.
        self.assertEqual(headers(self.render(path, live)), {'Authorization': 'Bearer live-token'})
        self.assertIsNone(headers(self.render(path, '')))
        env_file = self.home / '.config/environment.d/90-executor-mcp.conf'
        env_file.parent.mkdir(parents=True)
        env_file.write_text('OTHER=1\nEXECUTOR_MCP_TOKEN="file-token"\n')
        self.assertEqual(headers(self.render(path, live)), {'Authorization': 'Bearer file-token'})
        self.token = 'env-token'
        self.assertEqual(headers(self.render(path, live)), {'Authorization': 'Bearer env-token'})

    def test_pi_adapter_migration_preserves_unrelated_options(self):
        path = 'private_dot_pi/private_agent/modify_mcp.json'
        before = {'settings': {'hostConfigDiscovery': 'off', 'toolPrefix': 'server',
                               'scriptMode': False, 'outputGuard': {'maxBytes': 51200},
                               'customOption': True}}
        after = self.render(path, json.dumps(before))
        self.assertEqual(after['settings'], {'customOption': True})
        self.assertEqual(after['mcpServers']['executor']['exposure'], 'direct')
        self.assertNotIn('settings', self.render(path, '{"settings":{"scriptMode":false}}'))

    def test_opencode_jsonc_cannot_reintroduce_servers(self):
        path = 'private_dot_config/opencode/modify_opencode.jsonc'
        before = '{ // host config\n"theme": "local", "mcp": {"playwriter": {}}, }'
        after = self.render(path, before)
        self.assertEqual(after, {'theme': 'local'})
        self.assertEqual(self.render(path, json.dumps(after)), after)
        self.assertEqual(self.render(path, ''), {})


if __name__ == '__main__':
    unittest.main()
