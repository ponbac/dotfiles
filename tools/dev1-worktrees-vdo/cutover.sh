#!/bin/bash
# One-shot move of dev-1's ~/.t3/worktrees onto the dev1data XFS + VDO volume (2026-11-10).
#
#   cutover.sh --check     preflight only: nothing is stopped or changed
#   cutover.sh --run       stop T3, final sync, verify, swap the mount, start T3
#
# Run --run detached (systemd-run --user), because stopping T3 ends every agent session. It waits
# until no T3 run is active, aborts (T3 started again, nothing changed) if anything still uses the
# worktrees or a check fails before the swap, and rolls the swap back if a check fails after it.
# Log: ~/.local/state/dev1-cleanup/cutover.log, outcome in cutover.status.
# The old ext4 copy stays at ~/.t3/worktrees.ext4-old (and ~/.bun/install/cache.ext4-old) until
# it is deleted by hand after a week.
set -uo pipefail

WT=/home/ponbac/.t3/worktrees
NEW=/mnt/newwt
OLD=/home/ponbac/.t3/worktrees.ext4-old
BUNDIR=/home/ponbac/.bun/install
DEV=/dev/mapper/dev1data-worktrees
UUID=e4ed599a-6a6b-4317-9d3c-ca1daf5ce0de
FSTAB_LINE="UUID=$UUID $WT xfs noatime,nofail,x-systemd.before=user@1000.service,x-systemd.device-timeout=3min 0 0"
DROPIN_SRC=/home/ponbac/.local/share/chezmoi/private_dot_config/systemd/user/t3code.service.d/20-worktrees-mount.conf
DROPIN=/home/ponbac/.config/systemd/user/t3code.service.d/20-worktrees-mount.conf
DB=/home/ponbac/.t3/userdata/statev2.sqlite
STATE=/home/ponbac/.local/state/dev1-cleanup
STATUS=$STATE/cutover.status
WORK=$STATE/cutover-work
MODE=${1:-}
case "$MODE" in --check|--run) ;; *) echo "usage: $0 --check|--run" >&2; exit 2 ;; esac

mkdir -p "$STATE" "$WORK"
exec > >(tee -a "$STATE/cutover.log") 2>&1
log() { echo "$(date -Is) [$MODE] $*"; }
status() { echo "$(date -Is) $*" >"$STATUS"; log "STATUS: $*"; }
die_unchanged() { status "ABORTED, nothing changed: $*"; exit 1; }

running_runs() { sqlite3 -readonly "file:$DB?mode=ro" "select count(*) from orchestration_v2_projection_runs where status='running';" 2>/dev/null || echo error; }
users_of_wt() { # pid:comm of processes with cwd or an open file under the worktrees
  local p pid
  for p in /proc/[0-9]*; do
    pid=${p#/proc/}
    { readlink "$p/cwd"; find "$p/fd" -maxdepth 1 -type l -printf '%l\n'; } 2>/dev/null \
      | grep -q -E "^$WT(/|$)" && printf '%s:%s ' "$pid" "$(cat "$p/comm" 2>/dev/null)"
  done
}
sync_cmd() { # extra rsync flags...; worktrees content at the volume root, bun cache under cache/
  rsync -aH --numeric-ids --delete --relative "$@" "$WT/./" "$BUNDIR/./cache" "$NEW/"
}
sample_worktrees() { find "$WT" -mindepth 3 -maxdepth 3 -name .git -type f -printf '%h\n' | sort | awk 'NR % 9 == 1' | head -10; }
git_snapshot() { # out-file: porcelain status of the sample worktrees (read-only: no index refresh)
  local wt
  while IFS= read -r wt; do
    echo "== ${wt#"$WT/"}"
    GIT_OPTIONAL_LOCKS=0 git -C "$wt" status --porcelain=v1 --untracked-files=all 2>&1 | sort
  done <"$WORK/sample" >"$1"
}

# ------------------------------------------------------------------ preflight (no changes)
log "preflight"
[ "$(findmnt -n -o SOURCE --mountpoint "$NEW")" = "$DEV" ] || die_unchanged "$NEW is not the VDO volume"
! mountpoint -q "$WT" || die_unchanged "$WT is already a mount point"
[ ! -e "$OLD" ] || die_unchanged "$OLD already exists"
[ ! -e "$BUNDIR/cache.ext4-old" ] || die_unchanged "$BUNDIR/cache.ext4-old already exists"
[ -d "$BUNDIR/cache" ] && [ ! -L "$BUNDIR/cache" ] || die_unchanged "$BUNDIR/cache is not a plain directory"
! grep -q "[[:space:]]${WT}[[:space:]]" /etc/fstab || die_unchanged "/etc/fstab already has $WT"
[ -f "$DROPIN_SRC" ] || die_unchanged "missing $DROPIN_SRC"
sudo -n true || die_unchanged "sudo needs a password"
pending=$(sync_cmd -n --itemize-changes | grep -c -v '^\.d\.\.t\.\.\.\.\.\.' || true)
log "rsync dry run: $pending item(s) to transfer since the last sync"
if [ "$MODE" = --check ]; then
  log "running T3 runs: $(running_runs); users of worktrees: $(users_of_wt)"
  status "CHECK OK ($pending pending items)"
  exit 0
fi

# ------------------------------------------------------------------ wait for idle T3, stop it
status "waiting for T3 to be idle"
sleep 120   # let the launching agent finish its reply
for i in $(seq 1 60); do
  n=$(running_runs)
  [ "$n" = 0 ] && break
  [ "$i" = 60 ] && die_unchanged "T3 still has $n running run(s) after 20 minutes"
  sleep 20
done
log "no running T3 runs; stopping t3code.service"
systemctl --user stop t3code.service
start_t3_and_die() { systemctl --user start t3code.service; status "ABORTED before swap, T3 restarted: $*"; exit 1; }
for i in $(seq 1 12); do
  u=$(users_of_wt)
  [ -z "$u" ] && break
  [ "$i" = 12 ] && start_t3_and_die "still in use after T3 stopped: $u"
  log "waiting for: $u"; sleep 5
done

# ------------------------------------------------------------------ final sync and verification
status "final sync"
sync_cmd || start_t3_and_die "final rsync failed"
sync
left=$(sync_cmd -n --itemize-changes | grep -c -v '^\.d\.\.t\.\.\.\.\.\.' || true)
[ "$left" = 0 ] || start_t3_and_die "$left item(s) still differ after the final sync"
src_files=$(find "$WT" "$BUNDIR/cache" -type f | wc -l)
dst_files=$(find "$NEW" -type f | wc -l)
log "files: ext4 $src_files, VDO $dst_files"
[ "$src_files" = "$dst_files" ] || start_t3_and_die "file count differs: $src_files vs $dst_files"
sample_worktrees >"$WORK/sample"
log "sample: $(paste -sd ' ' "$WORK/sample")"
# Content check on the sample's source files (node_modules and build output are covered by size+mtime).
while IFS= read -r wt; do
  rel=${wt#"$WT/"}
  diffs=$(rsync -anc --itemize-changes --exclude=node_modules --exclude=bin --exclude=obj --exclude=target \
    "$wt/" "$NEW/$rel/" | grep -c -v '^\.d' || true)
  [ "$diffs" = 0 ] || start_t3_and_die "checksum differences in $rel: $diffs"
done <"$WORK/sample"
git_snapshot "$WORK/git-before"
log "verified; swapping"

# ------------------------------------------------------------------ swap (rolled back on failure)
rollback() {
  log "ROLLBACK: $*"
  systemctl --user stop t3code.service
  rm -f "$DROPIN"; systemctl --user daemon-reload
  if [ -L "$BUNDIR/cache" ]; then rm -f "$BUNDIR/cache"; fi
  [ ! -d "$BUNDIR/cache.ext4-old" ] || mv "$BUNDIR/cache.ext4-old" "$BUNDIR/cache"
  ! mountpoint -q "$WT" || sudo umount "$WT"
  if [ -d "$OLD" ]; then
    sudo chattr -i "$WT" 2>/dev/null; rmdir "$WT" 2>/dev/null; mv "$OLD" "$WT"
  fi
  [ ! -f "$WORK/fstab.bak" ] || sudo cp "$WORK/fstab.bak" /etc/fstab
  sudo systemctl daemon-reload
  sudo mount -o noatime "$DEV" "$NEW" 2>/dev/null
  systemctl --user start t3code.service
  status "ROLLED BACK, T3 restarted on ext4: $*"
  exit 1
}
cp /etc/fstab "$WORK/fstab.bak"
sudo umount "$NEW" || start_t3_and_die "cannot unmount $NEW"
mv "$WT" "$OLD" || rollback "mv to $OLD failed"
mkdir -m 700 "$WT" && sudo chattr +i "$WT" || rollback "cannot create the locked mount point"
printf '# T3 worktrees: dev1data XFS + VDO volume (dotfiles tools/dev1-worktrees-vdo)\n%s\n' "$FSTAB_LINE" \
  | sudo tee -a /etc/fstab >/dev/null || rollback "cannot update /etc/fstab"
sudo systemctl daemon-reload
sudo mount "$WT" || rollback "mount from fstab failed"
[ "$(findmnt -n -o SOURCE --mountpoint "$WT")" = "$DEV" ] || rollback "$WT is not the VDO volume after mounting"
mv "$WT/cache" "$WT/.bun-cache" || rollback "cannot rename the bun cache"
mv "$BUNDIR/cache" "$BUNDIR/cache.ext4-old" && ln -s "$WT/.bun-cache" "$BUNDIR/cache" || rollback "bun cache symlink failed"
mkdir -p "$(dirname "$DROPIN")" && cp "$DROPIN_SRC" "$DROPIN" && systemctl --user daemon-reload || rollback "T3 drop-in failed"
git_snapshot "$WORK/git-after"
cmp -s "$WORK/git-before" "$WORK/git-after" || rollback "git status differs: $(diff "$WORK/git-before" "$WORK/git-after" | head -5 | tr '\n' ' ')"

# ------------------------------------------------------------------ start T3
systemctl --user start t3code.service
sleep 15
systemctl --user is-active -q t3code.service || rollback "t3code.service did not start"
status "DONE: $WT on $DEV; $(df -h --output=used "$WT" | tail -1 | tr -d ' ') logical; old copy at $OLD"
