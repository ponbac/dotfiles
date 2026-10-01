#!/usr/bin/env python3
"""Preview or deploy this allowlisted source to the three known hosts."""
import argparse
import atexit
import datetime
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
HOSTS = ("omarchy", "dev-1", "omarchy-laptop")
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]


def run_host(host, argv, **kwargs):
    if host == os.uname().nodename:
        return subprocess.run(argv, check=True, **kwargs)
    return subprocess.run(SSH + ["ponbac@" + host, shlex.join(argv)], check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hosts", nargs="*", help="Default: all three known hosts")
    parser.add_argument("--apply", action="store_true", help="Back up, install source, and apply")
    parser.add_argument("--bootstrap", action="store_true", help="Also install agents/Herdr and reconcile integrations and pinned Pi packages (requires --apply)")
    args = parser.parse_args()
    if args.bootstrap and not args.apply:
        parser.error("--bootstrap requires --apply")
    hosts = args.hosts or HOSTS
    if any(h not in HOSTS for h in hosts):
        parser.error("Only omarchy, dev-1, and omarchy-laptop are supported")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    snapshot_root = Path(tempfile.mkdtemp(prefix="chezmoi-deploy-"))
    atexit.register(shutil.rmtree, snapshot_root, ignore_errors=True)
    snapshot = snapshot_root / "source"
    shutil.copytree(SOURCE, snapshot, symlinks=True, ignore=shutil.ignore_patterns('.git'))
    for host in hosts:
        print(f"\n=== {host}: {'APPLY' if args.apply else 'PREVIEW'} ===", flush=True)
        # Upload into a staging directory; preview never replaces the source repository.
        stage = f"/home/ponbac/.cache/chezmoi-deploy/{stamp}"
        run_host(host, ["mkdir", "-p", stage])
        destination = stage + "/" if host == os.uname().nodename else f"ponbac@{host}:{stage}/"
        subprocess.run(["rsync", "-a", "--delete", "--exclude=.git", str(snapshot) + "/", destination], check=True)
        program = r'''
import datetime,json,os,shutil,subprocess,sys
from pathlib import Path
stage=Path(sys.argv[1]); apply=sys.argv[2]=='yes'; home=Path.home()
cm=shutil.which('chezmoi') or str(home/'.local/bin/chezmoi')
def cmd(*args): return subprocess.check_output([cm,'--source',str(stage),*args],text=True)
# Rendering catches invalid templates before touching managed files. Don't print
# rendered contents: modify scripts can legitimately preserve local credentials.
subprocess.run([cm,'--source',str(stage),'apply','--dry-run','--no-tty'],check=True,stdout=subprocess.DEVNULL)
status=cmd('status','--no-pager')
lines=status.splitlines()
print(f'{len(lines)} paths would change')
for line in lines:
 if not any(part in line for part in ('.agents/skills/', '.pi/agent/extensions/', '.claude/skills/')):
  print(line)
if not apply: sys.exit(0)
source=Path(subprocess.check_output([cm,'source-path'],text=True).strip())
if source != home/'.local/share/chezmoi': raise SystemExit('Unexpected source directory; refusing deployment')
backup=home/'.local/state/chezmoi-deploy-backups'/stage.name
backup.mkdir(parents=True,mode=0o700,exist_ok=False)
# Source-state snapshots include Git metadata, so old source work is recoverable.
if source.exists(): shutil.copytree(source,backup/'source',symlinks=True)
config=home/'.config/chezmoi'
if config.exists(): shutil.copytree(config,backup/'chezmoi-state',symlinks=True)
managed=[p for p in cmd('managed','--include=files,symlinks','--nul-path-separator').split('\0') if p]
manifest=[]
for rel in managed:
 p=home/rel
 if not p.is_relative_to(home) or '..' in Path(rel).parts: raise SystemExit('Unsafe managed path')
 exists=p.exists() or p.is_symlink()
 manifest.append({'path':rel,'existed':exists})
 if exists:
  target=backup/'targets'/rel; target.parent.mkdir(parents=True,exist_ok=True)
  if p.is_symlink(): target.symlink_to(os.readlink(p))
  elif p.is_dir(): shutil.copytree(p,target,symlinks=True)
  else: shutil.copy2(p,target)
(backup/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
directory_modes={}
for rel in cmd('managed','--include=dirs','--nul-path-separator').split('\0'):
 if not rel: continue
 p=home/rel
 directory_modes[rel]=(p.stat().st_mode & 0o7777) if p.is_dir() and not p.is_symlink() else None
(backup/'directory-modes.json').write_text(json.dumps(directory_modes,indent=2)+'\n')
source.mkdir(parents=True,exist_ok=True)
subprocess.run(['rsync','-a','--delete','--exclude=.git',str(stage)+'/',str(source)+'/'],check=True)
if not (source/'.git').exists():
 subprocess.run(['git','init','--quiet',str(source)],check=True)
 subprocess.run(['git','-C',str(source),'remote','add','origin','https://github.com/ponbac/dotfiles.git'],check=True)
print('Recovery backup:',backup,flush=True)
subprocess.run([cm,'apply','--force','--no-tty'],check=True)
remaining=subprocess.check_output([cm,'status','--no-pager'],text=True)
print('Post-apply status:',remaining or 'clean',flush=True)
if remaining: raise SystemExit('Managed drift remains; inspect before proceeding')
'''
        run_host(host, ["python3", "-", stage, "yes" if args.apply else "no"], input=program, text=True)
        if args.bootstrap:
            run_host(host, ["bash", "/home/ponbac/.local/share/chezmoi/tools/bootstrap-agents.sh"])


if __name__ == "__main__":
    main()
