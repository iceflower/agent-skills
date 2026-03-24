---
name: git-workflow
description: >-
  Git commit conventions, branch strategy, and collaboration workflow rules.
  Covers conventional commits, commit message formatting, squash merge, rebase,
  interactive rebase, branch naming conventions, merge conflict resolution,
  cherry-pick, git bisect, and pull request workflows.
  Use when committing code, managing branches, resolving merge conflicts,
  or defining a team Git branching strategy.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# Git Workflow Rules

## 1. Commit Message Convention

### Format

```text
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### Types

| Type       | Description                         |
| ---------- | ----------------------------------- |
| `feat`     | New feature                         |
| `fix`      | Bug fix                             |
| `docs`     | Documentation changes               |
| `style`    | Code formatting (no logic change)   |
| `refactor` | Code refactoring                    |
| `test`     | Adding/updating tests               |
| `chore`    | Build/config changes                |
| `perf`     | Performance improvement             |
| `ci`       | CI/CD configuration changes         |
| `revert`   | Revert previous commit              |

### Writing Rules

- Subject line under 50 characters
- Use imperative mood (Add, Fix, Update, etc.)
- No period at end of subject
- Wrap body at 72 characters
- Explain "what" and "why" in body, not "how"

### Example

```text
feat(auth): Add JWT token refresh logic

Previously, users had to re-login when token expired.
Added refresh token mechanism for automatic renewal.

Closes #123
```

---

## 2. Branch Strategy

### Branch Structure

| Branch        | Purpose                | Protected |
| ------------- | ---------------------- | --------- |
| `main`        | Production deployment  | Yes       |
| `develop`     | Development integration| Yes       |
| `feature/*`   | Feature development    | No        |
| `release/*`   | Release preparation    | No        |
| `hotfix/*`    | Production hotfix      | No        |
| `bugfix/*`    | Bug fix (from develop) | No        |

### Branch Naming

```text
feature/<issue-number>-<short-description>   # e.g., feature/123-add-login
bugfix/<issue-number>-<short-description>    # e.g., bugfix/456-fix-auth-error
hotfix/<issue-number>-<short-description>    # e.g., hotfix/789-patch-crash
release/<version>                            # e.g., release/1.2.0
```

### Merge Strategy

- `feature` → `develop`: Squash and merge
- `release` → `main`: Merge commit
- `hotfix` → `main` + `develop`: Merge commit

---

## 3. Pull Request Guidelines

### PR Title

Same format as commit message: `<type>(<scope>): <subject>`

### PR Description Template

```markdown
## Summary

- Brief description of changes

## Changes

- Specific changes made

## Test Plan

- [ ] Test item 1
- [ ] Test item 2

## Screenshots (if UI changes)

## Related Issues

Closes #<issue-number>
```

### Pre-Review Checklist

- [ ] Commit message convention followed
- [ ] Unnecessary files/comments removed
- [ ] Conflicts resolved
- [ ] CI passed

---

## 4. Commit Practices

### Atomic Commits

- One commit = one logical change
- Do not mix "feature + bugfix + refactor" in single commit

### Commit Split Example

```text
# Bad
git commit -m "Add login feature and fix header bug and update README"

# Good
git commit -m "feat(auth): Add login feature"
git commit -m "fix(ui): Fix header alignment"
git commit -m "docs: Update README with login instructions"
```

### FAQ

#### How to amend the last commit message

```bash
git commit --amend
```

#### How to squash multiple commits

```bash
git rebase -i HEAD~3
```

---

## 5. Git Safety Rules

### Never Do

- `git push --force` on main/master/develop
- Commit secrets to public repositories
- Modify pushed commits after rebase/force push

### Recovery Guide

| Situation                     | Solution                           |
| ----------------------------- | ---------------------------------- |
| Committed to wrong branch     | `git cherry-pick` or `git reset`   |
| Committed sensitive info      | `git filter-repo` or BFG Cleaner   |
| Want to undo merge            | `git reset --hard ORIG_HEAD`       |
| Restore specific file         | `git checkout HEAD~1 -- <file>`    |

---

## 6. Rebase Workflow

### Rebase vs Merge: When to Use Which

| Scenario                              | Recommended          |
| ------------------------------------- | -------------------- |
| Updating a local feature branch       | Rebase               |
| Integrating a shared/protected branch | Merge                |
| Cleaning up commit history before PR  | Rebase (interactive) |
| Preserving exact merge timeline       | Merge                |

**Golden rule**: Never rebase commits that have been pushed to a shared branch.

### Rebasing onto the Base Branch

```bash
# Update feature branch with latest changes from develop
git checkout feature/123-add-login
git fetch origin
git rebase origin/develop
```

### Interactive Rebase

Use `git rebase -i` to clean up commit history before opening a PR.

| Action   | Effect                                        |
| -------- | --------------------------------------------- |
| `pick`   | Keep the commit as-is                         |
| `reword` | Keep the commit but edit its message          |
| `squash` | Combine with previous commit, keep message    |
| `fixup`  | Combine with previous commit, discard message |
| `drop`   | Remove the commit entirely                    |

```bash
# Squash the last 4 commits into one
git rebase -i HEAD~4
```

### Handling Rebase Conflicts

1. Resolve conflicts in the affected files and stage them: `git add <file>`.
2. Continue: `git rebase --continue`.
3. To abort and restore the original state: `git rebase --abort`.

---

## 7. Cherry-pick

### Use Cases

- Backporting a bug fix from `develop` to a `release/*` or `hotfix/*` branch
- Applying a specific commit to another branch without merging the entire branch
- Recovering a commit from a deleted or abandoned branch

### Basic Usage

```bash
git cherry-pick <commit-hash>                       # single commit
git cherry-pick <hash-1> <hash-2>                   # multiple commits
git cherry-pick <start-hash>..<end-hash>            # range (exclusive of start)
```

### Important Considerations

- Cherry-picked commits get new hashes; the original and copy are independent.
- Avoid cherry-picking merge commits unless necessary (use `-m 1` to specify mainline parent).
- If the same change is later merged normally, expect potential conflicts.
- Always verify the result compiles and passes tests after cherry-picking.

---

## 8. Merge Conflict Resolution

### Prevention

- Rebase feature branches frequently, keep PRs small, and communicate about shared file ownership.

### Resolution Steps

1. Identify conflicting files: `git status` shows "both modified" entries.
2. Open each file, find conflict markers (`<<<<<<<` / `=======` / `>>>>>>>`), and decide which changes to keep.
3. Remove all conflict markers and stage resolved files: `git add <file>`.
4. Complete: `git commit` (for merge) or `git rebase --continue` (for rebase).

### Tools

| Tool       | Command / Setup                          |
| ---------- | ---------------------------------------- |
| vimdiff    | `git mergetool --tool=vimdiff`           |
| VS Code    | Open conflicting file; use inline UI     |
| IntelliJ   | VCS → Git → Resolve Conflicts            |
| `diff3`    | `git config merge.conflictstyle diff3`   |

Using `diff3` style adds the common ancestor between the two sides, making conflict resolution easier.

---

## 9. Git Bisect

### Purpose

Efficiently find the commit that introduced a bug using binary search.

### Basic Workflow

```bash
git bisect start
git bisect bad                   # mark current (broken) commit
git bisect good <known-good-hash> # mark a known-good commit

# Git checks out a middle commit — test it, then mark good or bad.
# Repeat until Git identifies the first bad commit.

git bisect reset                 # end session, return to original branch
```

### Automated Bisect

Provide a test script that exits 0 for good and non-zero for bad:

```bash
git bisect start HEAD <known-good-hash>
git bisect run ./test-script.sh
```

### Tips

- Choose a known-good commit as far back as practical to reduce iterations.
- The number of steps is approximately `log2(N)` where N is the number of commits in the range.
- If a commit cannot be tested (e.g., broken build), skip it: `git bisect skip`.

---

## 10. History Management

### Squash Merge

Combine all feature branch commits into a single commit. Ideal for branches with many WIP commits.

```bash
git checkout develop
git merge --squash feature/123-add-login
git commit -m "feat(auth): Add login feature"
```

### Fixup Commits

Create a commit intended to be squashed into a previous commit during rebase:

```bash
git commit --fixup=<target-hash>
git rebase -i --autosquash HEAD~5    # autosquash fixup commits
```

Tip: enable autosquash by default with `git config --global rebase.autosquash true`.

### Amend

Modify the most recent commit (message or content). Only use on unpushed commits.

```bash
git commit --amend -m "fix(auth): Correct token expiry check"  # change message
git add forgotten-file.ts && git commit --amend --no-edit       # add missed files
```

### When to Use Each

| Technique    | Scenario                                             |
| ------------ | ---------------------------------------------------- |
| Squash merge | Merging a feature branch with noisy history          |
| Fixup        | Addressing review feedback before merge              |
| Amend        | Fixing typos or adding missed files in latest commit |
| Reword       | Correcting a misleading commit message               |

---

## 11. Pull Request Workflow

### PR Size Guidelines

| Size        | Lines Changed | Recommendation         |
| ----------- | ------------- | ---------------------- |
| Small       | < 200         | Ideal                  |
| Medium      | 200–400       | Acceptable             |
| Large       | 400–800       | Consider splitting     |
| Extra large | > 800         | Split into smaller PRs |

### Splitting Large PRs

- Separate refactoring from feature work; split backend/frontend when possible.
- Use stacked PRs: PR1 (base) → PR2 (builds on PR1) → PR3.

### Draft PRs

Use draft PRs for work-in-progress needing early feedback, dependent changes, or experimental spikes. Convert to ready when all checks pass and the work is complete.

```bash
gh pr create --draft --title "feat(auth): Add OAuth2 flow" --body "WIP: seeking feedback"
```

### Reviewer Assignment

- Assign at least one reviewer with domain knowledge of the changed area.
- For cross-cutting changes, assign reviewers from each affected team.
- Use `.github/CODEOWNERS` to automate reviewer assignment per directory.

### Review Etiquette

- Reviewers: provide actionable feedback; distinguish between blocking issues and suggestions.
- Authors: respond to all comments before merging; do not dismiss reviews without discussion.
- Use conventional comment prefixes: `nit:`, `suggestion:`, `question:`, `blocker:`.
