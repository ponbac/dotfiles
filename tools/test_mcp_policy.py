"""Render shared MCP policies without connecting servers or touching live config."""
import json
from pathlib import Path
import subprocess
import tomllib
import unittest

SOURCE = Path(__file__).resolve().parents[1]

POLICIES = (
    ('private_dot_pi/private_agent/modify_mcp.json', 'mcpServers'),
    ('modify_private_dot_claude.json', 'mcpServers'),
    ('private_dot_codex/modify_config.toml', 'mcp_servers'),
    ('private_dot_config/opencode/modify_opencode.json', 'mcp'),
)


class MCPPolicyTests(unittest.TestCase):
    def render(self, path, current):
        template = (SOURCE / path).read_text()
        data = {'chezmoi': {'sourceDir': str(SOURCE), 'stdin': current}}
        output = subprocess.check_output(
            ['chezmoi', '--source', str(SOURCE), '--override-data', json.dumps(data),
             'execute-template', template], text=True,
        )
        return tomllib.loads(output) if path.endswith('.toml') else json.loads(output)

    def test_executor_only_preserves_unrelated_settings_and_is_idempotent(self):
        for path, key in POLICIES:
            with self.subTest(path=path):
                if path.endswith('.toml'):
                    before = ('local_setting = "keep"\n'
                              '[mcp_servers.railway]\ncommand = "railway"\n'
                              '[mcp_servers.executor]\nurl = "https://wrong.invalid"\n'
                              'bearer_token = "host-secret"\n')
                else:
                    before = json.dumps({'local_setting': 'keep', key: {
                        'railway': {'command': ['railway', 'mcp']},
                        'playwriter': {'enabled': False},
                        'executor': {'url': 'https://wrong.invalid',
                                     'headers': {'Authorization': 'host-secret'}},
                    }})
                after = self.render(path, before)
                self.assertEqual(after['local_setting'], 'keep')
                self.assertEqual(set(after[key]), {'executor'})
                executor = after[key]['executor']
                self.assertEqual(executor['url'], 'https://executor.pike-quail.ts.net/mcp')
                self.assertNotIn('host-secret', json.dumps(after))
                if key == 'mcp_servers':
                    self.assertEqual(executor['bearer_token_env_var'], 'EXECUTOR_MCP_TOKEN')
                    self.assertEqual(executor['default_tools_approval_mode'], 'writes')
                    # These are the only top-level settings exercised by this fixture.
                    again = ('local_setting = "keep"\n[mcp_servers.executor]\n' +
                             '\n'.join(f'{k} = {json.dumps(v)}' for k, v in executor.items()))
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
