"""Render the MCP migration without connecting servers or touching live config."""
import json
from pathlib import Path
import subprocess
import unittest

SOURCE = Path(__file__).resolve().parents[1]


class MCPPolicyTests(unittest.TestCase):
    def render(self, current):
        template = (SOURCE / 'private_dot_pi/private_agent/modify_mcp.json').read_text()
        data = {'chezmoi': {'sourceDir': str(SOURCE), 'stdin': json.dumps(current)}}
        output = subprocess.check_output(
            ['chezmoi', '--source', str(SOURCE), '--override-data', json.dumps(data),
             'execute-template', template], text=True,
        )
        return json.loads(output)

    def test_adapter_migration_preserves_unrelated_servers_and_options(self):
        other = {'command': 'local-server', 'env': {'TOKEN': '${OTHER_TOKEN}'}}
        before = {
            'settings': {'hostConfigDiscovery': 'off', 'toolPrefix': 'server',
                         'scriptMode': False, 'outputGuard': {'maxBytes': 51200},
                         'customOption': True},
            'mcpServers': {
                'other': other,
                'executor': {
                    'auth': 'bearer', 'bearerTokenEnv': 'EXECUTOR_MCP_TOKEN',
                    'lifecycle': 'lazy', 'directTools': True, 'approveTools': False,
                    'headers': {'X-Host-Header': '${HOST_VALUE}'}, 'timeout': 90,
                },
            },
        }
        after = self.render(before)
        self.assertEqual(after['settings'], {'customOption': True})
        self.assertEqual(after['mcpServers']['other'], other)
        self.assertEqual(after['mcpServers']['executor'], {
            'url': 'https://executor.pike-quail.ts.net/mcp',
            'headers': {'X-Host-Header': '${HOST_VALUE}',
                        'Authorization': 'Bearer ${EXECUTOR_MCP_TOKEN}'},
            'exposure': 'direct', 'timeout': 90,
        })
        self.assertEqual(self.render(after), after)

    def test_fresh_config_and_empty_legacy_settings_produce_native_config(self):
        expected = {'mcpServers': {'executor': {
            'url': 'https://executor.pike-quail.ts.net/mcp',
            'headers': {'Authorization': 'Bearer ${EXECUTOR_MCP_TOKEN}'},
            'exposure': 'direct',
        }}}
        for before in ({}, {'settings': {'scriptMode': False}}):
            with self.subTest(before=before):
                self.assertEqual(self.render(before), expected)


if __name__ == '__main__':
    unittest.main()
