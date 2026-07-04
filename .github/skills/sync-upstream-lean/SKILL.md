---
name: sync-upstream-lean
description: 'Sync this my-pylean fork with the upstream QuantConnect/Lean repository via a merge that preserves local contributions. Use when the user asks to "sync upstream", "update from QuantConnect", "pull upstream Lean", "merge upstream/master", or "catch up the fork".'
---

# Sync Upstream (QuantConnect Lean)

## Goal
Bring this fork (`my-pylean`) up to date with the upstream `QuantConnect/Lean` repository
while **preserving all local contributions** (custom scripts, docs, backtests, and the
intentional removal of `Tests/`, `Data/`, `Documentation/`, and CI workflows to slim the repo).

The proven strategy for this fork is a **merge** of `upstream/master` into `master`
(not a rebase of `master`), matching prior history:
`5d1ae0285 Merge upstream/master while preserving local contributions`.

## Trigger Phrases
- "sync my-pylean with upstream"
- "update from QuantConnect Lean"
- "pull upstream / merge upstream/master"
- "catch the fork up to upstream"

## Preconditions / Remotes
This repo is already configured with:
- `origin`   -> the fork (e.g. `github.com/<user>/my-pylean.git`)
- `upstream` -> `github.com/QuantConnect/Lean.git`

Verify with `git remote -v`. If `upstream` is missing:
```bash
git remote add upstream https://github.com/QuantConnect/Lean.git
```

## Process

### 1. Assess state (never skip)
```bash
git branch --show-current            # expect: master
git status -sb                       # note any uncommitted work
git fetch upstream                   # non-destructive
git rev-list --count HEAD..upstream/master   # commits BEHIND
git rev-list --count upstream/master..HEAD   # commits AHEAD (local contributions)
```

### 2. Handle uncommitted changes BEFORE merging
A merge requires a clean tree. Ask the user how to handle any dirty state
(commit / stash / discard). Default recommendation: **commit local work to `master`**.

Guardrails:
- **Never commit virtual environments.** Ensure `.venv/` and `pylean/` are in `.gitignore`.
- Watch for large blobs (>5 MB) sneaking into the commit:
  ```bash
  git diff --cached --name-only | while read f; do
    [ -f "$f" ] && sz=$(stat -c%s "$f") && [ "$sz" -gt 5242880 ] && echo "$((sz/1024/1024))MB  $f"
  done
  ```

### 3. Merge upstream into master
```bash
git merge upstream/master --no-edit \
  -m "Merge upstream/master (QuantConnect Lean) while preserving local contributions"
```

### 4. Resolve conflicts (fork-specific)
This fork deliberately deleted `Tests/`, `Data/`, `Documentation/`, and
`.github/workflows/`. Upstream keeps changing those files, so almost every conflict is
**`DU` = "deleted by us, modified by upstream"**. The correct, consistent resolution is to
**keep them deleted**:
```bash
# Confirm all conflicts are DU and located only in the intentionally-removed areas:
git status --porcelain | grep -E '^(DU|UD|AA|UU|DD|AU|UA)' | awk '{print $1}' | sort | uniq -c
git status --porcelain | grep '^DU' | awk '{print $2}' | cut -d/ -f1 | sort | uniq -c

# Keep them deleted:
git status --porcelain | grep '^DU' | awk '{print $2}' | while read f; do git rm -q "$f"; done
```
If any conflict is a real content conflict (`UU`) in a file the fork actually maintains
(e.g. a customized `.cs`/`.py` source file, `readme.md`, `.vscode/*`), resolve it manually:
keep upstream's functional changes and re-apply the local customization. Do not blindly
discard local edits.

Verify no conflicts remain:
```bash
git diff --name-only --diff-filter=U   # must be empty
```

### 5. Complete and verify
```bash
git commit --no-edit
git rev-list --count HEAD..upstream/master   # expect 0 (fully caught up)
git rev-list --count upstream/master..HEAD   # local contributions still ahead
# Spot-check custom files survived:
for f in PYLEAN_SETUP.md custom_dev.md rebase_organization_branches.sh \
         es_ma_crossover_clickhouse_backtest_pylean.py; do
  [ -e "$f" ] && echo "OK $f" || echo "MISSING $f"
done
git merge-base --is-ancestor upstream/master HEAD && echo "upstream fully merged"
```

### 6. Publish (only if the user confirms)
```bash
git push origin master
```
The merge brings in a large number of upstream commits, so the push may be sizable.
Do **not** push automatically unless the user asks.

## Safety Rules
- Do the non-destructive `fetch` and assessment before touching the working tree.
- Never discard uncommitted work without explicit user confirmation.
- Never commit `.venv/`, `pylean/`, or other virtualenvs / large generated data.
- Prefer `merge` over rebase for this fork to keep contribution history intact.
- Only `git rm` conflicts that fall inside the fork's intentionally-removed directories
  (`Tests/`, `Data/`, `Documentation/`, `.github/workflows/`). Anything else gets a manual review.

## Success Criteria
- `HEAD..upstream/master` count is `0`.
- Local contribution commits remain (`upstream/master..HEAD` > 0).
- Custom scripts/docs still present; no virtualenv or large blob committed.
- Working tree clean.
