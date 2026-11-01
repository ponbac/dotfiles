#!/usr/bin/env python3
"""Read-only exporter for T3 Code thread history (statev2.sqlite).

  index  [--since YYYY-MM-DD]                      one JSON line per thread, to stdout
  sample INDEX.jsonl ... [--seed N --random N --signal N --exclude ID,...]
                                                   JSON lines: a stratified random pick plus high-signal threads
  pack   --sample FILE --out DIR                   one markdown transcript per sampled thread, plus INDEX.tsv
  render --ids ID,ID,...                           JSON {thread_id: markdown}, to stdout

The database is opened with mode=ro, so nothing is written to it. index and render write to
stdout only, so the same file can be piped to another host, which is what pack does:
  ssh dev-1 python3 -I - index --host dev-1 < session_export.py
"""
import argparse
import collections
import json
import os
import random
import shlex
import sqlite3
import subprocess
import sys

HUMAN_SOURCES = ('web', 'mobile', 'mcp')


def connect(path):
    uri = 'file:' + os.path.expanduser(path) + '?mode=ro'
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    return db


def thread_meta(row):
    p = json.loads(row['payload_json'])
    sel = p.get('modelSelection') or {}
    opts = {o.get('id'): o.get('value') for o in sel.get('options') or [] if isinstance(o, dict)}
    prs = []
    for pr in p.get('pullRequests') or []:
        snap = pr.get('snapshot') or {}
        watch = pr.get('endedWatch') or {}
        prs.append({'url': pr.get('url'), 'state': snap.get('state'), 'checks': snap.get('checksState'),
                    'watchPassed': watch.get('passed'), 'failedChecks': watch.get('failedChecks')})
    lineage = p.get('lineage') or {}
    return {
        'id': row['thread_id'], 'title': row['title'], 'provider': row['default_provider'],
        'model': sel.get('model'), 'effort': opts.get('effort'),
        'source': p.get('creationSource'), 'createdBy': p.get('createdBy'),
        'parent': lineage.get('parentThreadId'), 'branch': p.get('branch'),
        'worktree': p.get('worktreePath'), 'created': row['created_at'], 'updated': row['updated_at'],
        'archived': bool(row['archived_at']), 'deleted': bool(row['deleted_at']), 'prs': prs,
    }


def index(db, host, since):
    projects = {r['project_id']: (r['title'], r['workspace_root'])
                for r in db.execute('select project_id, title, workspace_root from projection_projects')}
    counts = {}
    q = '''select i.thread_id, i.type, i.status, count(*) n from orchestration_v2_projection_turn_items i
           join orchestration_v2_projection_threads t using(thread_id)
           where t.created_at >= ? group by 1, 2, 3'''
    for r in db.execute(q, (since,)):
        c = counts.setdefault(r['thread_id'], {})
        c[r['type']] = c.get(r['type'], 0) + r['n']
        if r['status'] in ('failed', 'interrupted', 'cancelled'):
            key = r['type'] + ':' + r['status']
            c[key] = c.get(key, 0) + r['n']
    for row in db.execute('select * from orchestration_v2_projection_threads where created_at >= ? '
                          'order by created_at', (since,)):
        m = thread_meta(row)
        m['host'] = host
        m['project'], m['root'] = projects.get(row['project_id'], (None, None))
        m['counts'] = counts.get(row['thread_id'], {})
        print(json.dumps(m))


def clip(text, limit, tail=False):
    text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
    if len(text) <= limit:
        return text
    cut = len(text) - limit
    return ('[...%d chars cut...]\n' % cut + text[-limit:]) if tail else (text[:limit] + '\n[...%d chars cut...]' % cut)


def render_item(p):
    t, status = p.get('type'), p.get('status')
    bad = status in ('failed', 'interrupted', 'cancelled')
    flag = ' **[%s]**' % status.upper() if bad else ''
    if t == 'user_message':
        return '\n### USER (%s/%s)\n%s\n' % (p.get('creationSource'), p.get('createdBy'), clip(p.get('text') or '', 6000))
    if t == 'assistant_message':
        return '\n**ASSISTANT:** %s\n' % clip(p.get('text') or '', 3000)
    if t == 'command_execution':
        out = p.get('output') or ''
        return '\n`$ %s`%s\n```\n%s\n```\n' % (clip(p.get('input') or '', 500).replace('\n', ' ⏎ '), flag,
                                              clip(out, 1200, tail=True) if bad else clip(out, 300))
    if t == 'dynamic_tool':
        return '\n[tool %s]%s in: %s\n  out: %s\n' % (p.get('toolName'), flag, clip(p.get('input') or '', 500),
                                                   clip(p.get('output') or '', 1200 if bad else 400))
    if t == 'file_change':
        diff = p.get('diffStr') or ''
        plus = sum(1 for l in diff.splitlines() if l.startswith('+') and not l.startswith('+++'))
        minus = sum(1 for l in diff.splitlines() if l.startswith('-') and not l.startswith('---'))
        return '\n[edit %s +%d -%d]%s\n```diff\n%s\n```\n' % (p.get('fileName'), plus, minus, flag, clip(diff, 600))
    if t == 'subagent':
        return '\n[subagent %s child=%s]%s\n  prompt: %s\n  result: %s\n' % (
            p.get('driver'), p.get('childThreadId'), flag, clip(p.get('prompt') or '', 800), clip(p.get('result') or '', 1200))
    if t == 'reasoning':
        return ''
    if t == 'web_search':
        return '\n[web_search] %s\n' % clip(p.get('query') or p.get('title') or '', 200)
    return '\n[%s]%s %s\n' % (t, flag, clip(p.get('summary') or p.get('title') or '', 300))


def render(db, host, ids, budget=90000):
    out = {}
    for tid in ids:
        row = db.execute('select * from orchestration_v2_projection_threads where thread_id=?', (tid,)).fetchone()
        if not row:
            continue
        m = thread_meta(row)
        head = '# %s\n\nhost=%s provider=%s model=%s effort=%s source=%s/%s created=%s branch=%s\nPRs: %s\n' % (
            m['title'], host, m['provider'], m['model'], m['effort'], m['source'], m['createdBy'],
            m['created'], m['branch'], json.dumps(m['prs']))
        parts = [render_item(json.loads(r['payload_json'])) for r in db.execute(
            'select payload_json from orchestration_v2_projection_turn_items where thread_id=? '
            'order by ordinal, turn_item_id', (tid,))]
        body = ''.join(parts)
        if len(body) > budget:
            # Keep the start (task setup, usually where the first failure is) and the end (outcome).
            body = body[:budget * 2 // 3] + '\n\n[...%d chars of the middle cut...]\n\n' % (
                len(body) - budget) + body[-budget // 3:]
        out[tid] = head + body
    json.dump(out, sys.stdout)


def in_pool(r):
    c = r['counts']
    return (r['source'] in HUMAN_SOURCES and not r['deleted'] and c.get('user_message', 0) >= 1
            and c.get('command_execution', 0) + c.get('dynamic_tool', 0) >= 3)


def signal_score(r):
    c = r['counts']
    return (5 * c.get('command_execution:failed', 0) / max(1, c.get('command_execution', 1))
            + 3 * c.get('run_interrupt_request', 0) + 2 * c.get('user_input_request', 0)
            + min(c.get('user_message', 0), 12) / 3 + c.get('dynamic_tool:failed', 0) / 3 + c.get('compaction', 0)
            + sum(3 for p in r['prs'] if p['state'] == 'closed' or p['watchPassed'] is False))


def sample(paths, seed, n_random, n_signal, exclude):
    rows = [json.loads(line) for path in paths for line in open(path)]
    pool = [r for r in rows if in_pool(r) and r['id'] not in exclude]
    rng = random.Random(seed)
    strata = collections.defaultdict(list)
    for r in pool:
        strata[(r['host'], r['provider'])].append(r)
    picked = []
    for _, group in sorted(strata.items()):
        n = min(round(n_random * len(group) / len(pool)), len(group))
        picked += [dict(r, bucket='random') for r in rng.sample(group, n)]
    taken = {r['id'] for r in picked}
    seen = collections.Counter()
    signal = []
    for r in sorted((r for r in pool if r['id'] not in taken), key=signal_score, reverse=True):
        key = (r['host'], r['provider'], r['project'])  # at most two per project, so one bad week can't fill the bucket
        if len(signal) < n_signal and seen[key] < 2:
            seen[key] += 1
            signal.append(dict(r, bucket='signal'))
    print('pool %d, picked %d' % (len(pool), len(picked) + len(signal)), file=sys.stderr)
    for r in picked + signal:
        print(json.dumps(r))


def fetch_rendered(host, ids, db_path):
    args = ['render', '--host', host, '--ids', ','.join(ids)]
    if host == os.uname().nodename:
        cmd = [sys.executable, '-I', os.path.abspath(__file__), *args, '--db', db_path]
        stdin = subprocess.DEVNULL
    else:
        cmd = ['ssh', '-o', 'BatchMode=yes', host, 'python3 -I - ' + ' '.join(map(shlex.quote, args))]
        stdin = open(os.path.abspath(__file__))
    return json.loads(subprocess.run(cmd, stdin=stdin, capture_output=True, text=True, check=True).stdout)


def pack(sample_path, out_dir, db_path):
    rows = [json.loads(line) for line in open(sample_path)]
    os.makedirs(out_dir, exist_ok=True)
    rendered = {}
    for host in sorted({r['host'] for r in rows}):
        rendered.update(fetch_rendered(host, [r['id'] for r in rows if r['host'] == host], db_path))
    lines = []
    for i, r in enumerate(rows, 1):
        name = '%02d-%s-%s-%s.md' % (i, r['host'], r['provider'], r['bucket'])
        text = rendered.get(r['id'], 'MISSING')
        with open(os.path.join(out_dir, name), 'w') as f:
            f.write('<!-- thread %s project=%s bucket=%s -->\n%s' % (r['id'], r['project'], r['bucket'], text))
        lines.append('\t'.join((name, str(len(text)), str(r['project']), (r['title'] or '')[:70])))
    with open(os.path.join(out_dir, 'INDEX.tsv'), 'w') as f:
        f.write('\n'.join(lines) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=('index', 'sample', 'pack', 'render'))
    ap.add_argument('paths', nargs='*', help='index files, for sample')
    ap.add_argument('--db', default='~/.t3/userdata/statev2.sqlite')
    ap.add_argument('--host', default=os.uname().nodename)
    ap.add_argument('--since', default='2026-01-01')
    ap.add_argument('--ids', default='')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--random', type=int, default=28)
    ap.add_argument('--signal', type=int, default=12)
    ap.add_argument('--exclude', default='', help='thread ids to leave out, such as the current thread')
    ap.add_argument('--sample')
    ap.add_argument('--out')
    a = ap.parse_args()
    if a.mode == 'sample':
        return sample(a.paths, a.seed, a.random, a.signal, set(a.exclude.split(',')))
    if a.mode == 'pack':
        return pack(a.sample, a.out, a.db)
    db = connect(a.db)
    if a.mode == 'index':
        index(db, a.host, a.since)
    else:
        render(db, a.host, [i for i in a.ids.split(',') if i])


if __name__ == '__main__':
    main()
