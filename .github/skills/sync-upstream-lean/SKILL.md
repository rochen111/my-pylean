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

#### 6a. Authentication (origin is HTTPS by default, but this env has no HTTPS creds)
`origin` is configured for HTTPS (`https://github.com/<owner>/my-pylean.git`), and this
environment has **no stored HTTPS credentials** (`gh` not logged in, no `GH_TOKEN`), so an
HTTPS push fails with `could not read Username for 'https://github.com'`.

Use the existing SSH key instead:
```bash
ssh -o BatchMode=yes -T git@github.com          # expect: "Hi <user>! You've successfully authenticated"
git remote set-url origin git@github.com:<owner>/my-pylean.git
git push --dry-run origin master                # verify write access WITHOUT writing
git push origin master
```
The SSH key identifies whoever it belongs to (here `jyck613`). Pushing to another owner's
repo (e.g. `rochen111/my-pylean`) requires that user to have **write/collaborator access**
on the repo. A `--dry-run` that prints `! [remote rejected] ... denied to <user>` means
access is missing — the repo **owner** must add the user as a collaborator with Write
(Settings -> Collaborators, or `gh api -X PUT repos/<owner>/<repo>/collaborators/<user> -f permission=push`),
and the user must accept the invite.

#### 6b. Email-privacy push rejection (GH007)
If the pusher's GitHub account has "Keep my email address private" + "Block command line
pushes that expose my email", the push is rejected:
```
remote: error: GH007: Your push would publish a private email address.
```
This happens when local commits were authored with a real email (e.g. `user@gmail.com`).
Fix by re-authoring **only your own** commits to the account's noreply email, then push.

1. Find the account's numeric id and build the noreply address `<id>+<user>@users.noreply.github.com`:
   ```bash
   curl -s https://api.github.com/users/<user> | grep -E '"id"|"login"'
   git config user.email "<id>+<user>@users.noreply.github.com"   # fix future commits too
   ```
2. Rewrite ONLY non-upstream commits so upstream SHAs stay intact (critical — using a full
   `origin/master..HEAD` range re-hashes the pulled upstream commits and makes every future
   sync think it is 100+ commits "behind"). Scope with `--not upstream/master`:
   ```bash
   FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --env-filter '
   if [ "$GIT_AUTHOR_EMAIL" = "<old-email>" ]; then
     export GIT_AUTHOR_EMAIL="<id>+<user>@users.noreply.github.com"
   fi
   if [ "$GIT_COMMITTER_EMAIL" = "<old-email>" ]; then
     export GIT_COMMITTER_EMAIL="<id>+<user>@users.noreply.github.com"
   fi
   ' -- HEAD --not upstream/master
   ```
3. Verify, then push (force-with-lease if a previous bad attempt was already pushed):
   ```bash
   git rev-list --count HEAD..upstream/master     # must still be 0
   git merge-base --is-ancestor upstream/master HEAD && echo "upstream preserved"
   git log HEAD --not upstream/master --format='%ae %ce' | grep -c '<old-email>'   # must be 0
   git push --force-with-lease origin master
   ```

## Safety Rules
- Do the non-destructive `fetch` and assessment before touching the working tree.
- Never discard uncommitted work without explicit user confirmation.
- Never commit `.venv/`, `pylean/`, or other virtualenvs / large generated data.
- Prefer `merge` over rebase for this fork to keep contribution history intact.
- Only `git rm` conflicts that fall inside the fork's intentionally-removed directories
  (`Tests/`, `Data/`, `Documentation/`, `.github/workflows/`). Anything else gets a manual review.
- Push over **SSH** (this env lacks HTTPS creds); confirm write access with `git push --dry-run` first.
- On `GH007` email-privacy rejection, re-author only your own commits to the noreply email and
  scope any history rewrite with `--not upstream/master` so upstream SHAs are preserved.
- Set local `git config user.email` to the noreply address up front to avoid `GH007` entirely.

## Success Criteria
- `HEAD..upstream/master` count is `0` (before AND after any email rewrite).
- Local contribution commits remain (`upstream/master..HEAD` > 0).
- Custom scripts/docs still present; no virtualenv or large blob committed.
- No private email published in pushed commits.
- Working tree clean; `origin/master` in sync with local `master`.
