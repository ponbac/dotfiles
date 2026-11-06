"""dev1-cleanup contracts through the script itself, with an isolated HOME and stubbed external I/O.

Run: python3 -B -m unittest discover -s tools -p 'test_dev1_cleanup.py' -v
Real git and sqlite3 on fixture repos/DBs; gh, docker, df and mise are stubs. Nothing outside the
temporary HOME is touched (the script's /tmp root is redirected with DEV1_CLEANUP_TMP_ROOT).
SIGPIPE stays ignored in the child, as systemd runs it (IgnoreSIGPIPE=yes).
"""
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'private_dot_local/bin/executable_dev1-cleanup'
GIB_KB = 1024 * 1024
DAY = 86400

STUBS = {
    # Emulates `gh api repos/.../commits/<sha>/pulls --jq ...`: GH_MODE=422 prints GitHub's error
    # body on stdout and fails (what real gh does), GH_MODE=pr:<n> prints a merged PR number.
    'gh': r'''#!/bin/bash
case "${GH_MODE:-none}" in
  422) echo '{"message":"No commit found for SHA: x","status":"422"}'; exit 1 ;;
  pr:*) echo "${GH_MODE#pr:}" ;;
esac
''',
    # Records every call. `builder prune -a` (emergency) optionally "frees" disk via the df state file.
    'docker': r'''#!/bin/bash
echo "$*" >>"$HOME/docker.log"
[ "$1" = info ] && exit 0
if [ "$1 $2" = "builder prune" ] && [[ " $* " == *" -a "* ]] && [ -n "${DOCKER_FREES_TO_KB:-}" ]; then
  echo "$DOCKER_FREES_TO_KB" >"$DF_STATE"
fi
echo "Total reclaimed space: 0B"
''',
    # Free space comes from $DF_STATE (KB) when set; human-readable report lines use the real df.
    'df': r'''#!/bin/bash
if [ -n "${DF_STATE:-}" ] && [[ " $* " != *" -h "* ]]; then echo Avail; cat "$DF_STATE"; exit 0; fi
exec /usr/bin/df "$@"
''',
    'mise': '#!/bin/bash\nexit 0\n',
}

SCHEMA = '''
CREATE TABLE orchestration_v2_projection_threads (thread_id TEXT PRIMARY KEY, title TEXT, created_at TEXT,
  updated_at TEXT, archived_at TEXT, deleted_at TEXT, payload_json TEXT);
CREATE TABLE orchestration_v2_projection_runs (thread_id TEXT, status TEXT, requested_at TEXT, completed_at TEXT);
CREATE TABLE orchestration_v2_projection_messages (thread_id TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE orchestration_events (aggregate_kind TEXT, stream_id TEXT, event_type TEXT, occurred_at TEXT);
CREATE TABLE projection_threads (thread_id TEXT, title TEXT, worktree_path TEXT, archived_at TEXT,
  deleted_at TEXT, settled_at TEXT, updated_at TEXT);
'''


def iso(seconds_ago):
    return time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(time.time() - seconds_ago))


def age_tree(path, seconds_ago):
    stamp = time.time() - seconds_ago
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            os.utime(os.path.join(root, name), (stamp, stamp), follow_symlinks=False)
    os.utime(path, (stamp, stamp))


class Dev1CleanupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='dev1-cleanup-test-')
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.tmproot = self.home / 'tmproot'
        stubs = self.home / 'stubs'
        for p in (self.tmproot, stubs, self.home / 'tmp', self.home / '.t3/userdata'):
            p.mkdir(parents=True)
        for name, body in STUBS.items():
            (stubs / name).write_text(body)
            (stubs / name).chmod(0o755)
        gitconfig = self.home / 'gitconfig'
        gitconfig.write_text('[user]\n\tname = t\n\temail = t@example.invalid\n[init]\n\tdefaultBranch = main\n')
        self.env = {'HOME': str(self.home), 'USER': os.environ.get('USER', 'ponbac'), 'LANG': 'C.UTF-8',
                    'PATH': f'{stubs}:/usr/bin:/bin', 'TMPDIR': str(self.home / 'tmp'),
                    'GIT_CONFIG_GLOBAL': str(gitconfig), 'GIT_CONFIG_NOSYSTEM': '1',
                    'DEV1_CLEANUP_TMP_ROOT': str(self.tmproot)}
        self.report = self.home / '.local/state/dev1-cleanup/last-report.md'
        self.db_path = self.home / '.t3/userdata/statev2.sqlite'
        self.db = sqlite3.connect(self.db_path)
        self.db.executescript(SCHEMA)
        self.addCleanup(self.db.close)
        self.git('init', '-q', '--bare', str(self.home / 'origin.git'))
        self.main = self.home / '.t3/projects/p'
        self.git('clone', '-q', str(self.home / 'origin.git'), str(self.main))
        (self.main / 'README').write_text('x\n')
        self.git('-C', str(self.main), 'add', 'README')
        self.git('-C', str(self.main), 'commit', '-qm', 'init')
        self.git('-C', str(self.main), 'push', '-q', 'origin', 'main')

    def git(self, *args):
        subprocess.run(['git', *args], check=True, env=self.env, capture_output=True)

    def worktree(self, name, local_commit=False):
        path = self.home / '.t3/worktrees/p' / name
        self.git('-C', str(self.main), 'worktree', 'add', '-q', '-b', name, str(path))
        if local_commit:
            (path / 'feature').write_text('work\n')
            self.git('-C', str(path), 'add', 'feature')
            self.git('-C', str(path), 'commit', '-qm', 'feature')
        return path

    def thread(self, thread_id, path, active_ago=3 * DAY, updated_ago=None, status='completed', title=None,
               settled=True):
        """A thread on `path` whose last real activity (run + message) was `active_ago` ago."""
        updated = iso(active_ago if updated_ago is None else updated_ago)
        settled_at = f',"settledAt":"{iso(active_ago)}"' if settled else ''
        payload = f'{{"worktreePath":"{path}"{settled_at}}}'
        self.db.execute('INSERT INTO orchestration_v2_projection_threads VALUES (?,?,?,?,NULL,NULL,?)',
                        (thread_id, f'title {thread_id}' if title is None else title, iso(10 * DAY), updated, payload))
        self.db.execute('INSERT INTO orchestration_v2_projection_runs VALUES (?,?,?,?)',
                        (thread_id, status, iso(active_ago + 60), None if status == 'running' else iso(active_ago)))
        self.db.execute('INSERT INTO orchestration_v2_projection_messages VALUES (?,?,?)',
                        (thread_id, iso(active_ago), iso(active_ago)))
        self.db.commit()

    def run_cleanup(self, *args, **env):
        result = subprocess.run([str(SCRIPT), *args], env={**self.env, **env}, cwd=self.home,
                                capture_output=True, text=True, timeout=300, restore_signals=False)
        return result

    def apply(self, **env):
        return self.run_cleanup('--apply', '--count-settled', **env)

    def set_free_gib(self, gib):
        state = self.home / 'df-state'
        state.write_text(f'{gib * GIB_KB}\n')
        return str(state)

    # --- worktree safety -------------------------------------------------------------------------

    def test_failed_pr_lookup_never_counts_as_a_merged_pr(self):
        wt = self.worktree('unpushed', local_commit=True)
        self.thread('t1', wt)
        self.apply(GH_MODE='422')
        self.assertTrue(wt.exists(), 'worktree with unpushed commits was removed after a gh error')
        self.assertIn('PR lookup failed', self.report.read_text())

    def test_active_run_keeps_worktree_even_with_thousands_of_threads(self):
        # Thousands of real-length thread ids overflow the pipe buffer: the shape that made the old
        # `cut | grep -q` guard report "no active run" under ignored SIGPIPE. Titles stay short so
        # the old script reaches the guard instead of crashing on its `cut | head` title summary.
        for case, active in (('active', True), ('control', False)):
            with self.subTest(case):
                wt = self.worktree(f'merged-{case}')
                self.thread(f'a-{case}', wt, status='running' if active else 'completed', title='')
                for i in range(3000):
                    self.thread(f'mcp:launch:{case}-{i:064}', wt, title='')
                self.apply()
                self.assertEqual(wt.exists(), active)

    def test_quiet_period_uses_real_activity_not_projection_updates(self):
        # Squash-merged PR (HEAD only local, GitHub reports the merged PR). The projection row was
        # rewritten an hour ago (T3 restart) but the last run and message were three days ago.
        quiet = self.worktree('restart-touched', local_commit=True)
        self.thread('q1', quiet, active_ago=3 * DAY, updated_ago=3600)
        busy = self.worktree('really-active', local_commit=True)
        self.thread('b1', busy, active_ago=3600)
        self.apply(GH_MODE='pr:42')
        self.assertFalse(quiet.exists())
        self.assertTrue(busy.exists())

    def test_open_threads_count_as_done_only_after_seven_idle_days(self):
        idle = self.worktree('open-idle')
        self.thread('o1', idle, active_ago=8 * DAY, settled=False)
        recent = self.worktree('open-recent')
        self.thread('o2', recent, active_ago=2 * DAY, settled=False)
        unpushed = self.worktree('open-idle-unpushed', local_commit=True)
        self.thread('o3', unpushed, active_ago=8 * DAY, settled=False)
        self.apply()
        self.assertEqual([p.exists() for p in (idle, recent, unpushed)], [False, True, True])
        attention = self.report.read_text().split('## Needs your attention', 1)[1].split('\n## ', 1)[0]
        self.assertIn('open-idle-unpushed', attention)
        self.assertNotIn('open-recent', attention)

    # --- robustness ------------------------------------------------------------------------------

    def test_failing_section_does_not_stop_later_sections_or_the_report(self):
        self.db.close()
        self.db_path.write_text('not a database')
        result = self.apply()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('builder prune', (self.home / 'docker.log').read_text())
        self.assertIn('t3-worktrees', self.report.read_text())

    # --- /tmp retention --------------------------------------------------------------------------

    def tmp_dir(self, rel, entries, seconds_ago):
        path = self.tmproot / rel
        for entry in entries:
            (path / entry).mkdir(parents=True)
            (path / entry / 'f').write_text('x')
        age_tree(path, seconds_ago)
        return path

    def test_tmp_retention_removes_only_idle_build_output_review_copies_and_old_sessions(self):
        uid = os.getuid()
        cases = {  # path -> expected to survive
            self.tmp_dir('old-dotnet', ['bin', 'obj'], 2 * DAY): False,
            self.tmp_dir('new-dotnet', ['bin', 'obj'], 600): True,
            self.tmp_dir('repo-review.x1', ['src', 'node_modules'], 4 * DAY): False,
            self.tmp_dir('repo-review.x2', ['src', 'node_modules'], 2 * DAY): True,
            self.tmp_dir('repo-review-git', ['.git', 'src'], 10 * DAY): True,   # may hold unpushed commits
            self.tmp_dir('old-scratch', ['src'], 10 * DAY): True,              # neither build output nor review
            self.tmp_dir(f'claude-{uid}/proj/old-session', ['tasks'], 8 * DAY): False,
            self.tmp_dir(f'claude-{uid}/proj/new-session', ['tasks'], 1 * DAY): True,
        }
        self.apply()
        self.assertEqual({p.name: p.exists() for p in cases}, {p.name: keep for p, keep in cases.items()})

    # --- emergency and guard ---------------------------------------------------------------------

    def test_emergency_stops_once_free_space_reaches_target(self):
        uid = os.getuid()
        for case, frees in (('docker frees enough', True), ('still low', False)):
            with self.subTest(case):
                session = self.tmp_dir(f'claude-{uid}/proj/{case.replace(" ", "-")}', ['tasks'], 3 * DAY)
                state = self.set_free_gib(5)
                self.run_cleanup('--apply', '--emergency', DF_STATE=state,
                                 DOCKER_FREES_TO_KB=str(80 * GIB_KB) if frees else '')
                self.assertIn('builder prune -a -f', (self.home / 'docker.log').read_text())
                # A 3-day-old session survives the normal 7-day rule; only the emergency step takes it.
                self.assertEqual(session.exists(), frees)

    def test_guard_runs_cleanup_only_below_threshold(self):
        for gib, runs in ((100, False), (30, True)):
            with self.subTest(free_gib=gib):
                self.report.unlink(missing_ok=True)
                self.run_cleanup('--guard', DF_STATE=self.set_free_gib(gib))
                self.assertEqual(self.report.exists(), runs)
                if runs:
                    self.assertIn('(apply)', self.report.read_text())


if __name__ == '__main__':
    unittest.main()
