# Development guide

How to get set up to work on this repo, and how a release actually happens.
Written so a future session (human or Claude Code) can pick this project
back up without re-deriving any of it.

## Prerequisites

- **Python 3.14+** - `pytest-homeassistant-custom-component==0.13.345`
  (pinned in `requirements_test.txt`) requires it. An older Python silently
  resolves to a broken/ancient version of that package instead of failing
  loudly - always confirm `python3 --version` matches before debugging test
  failures that don't make sense.
- **`gh` CLI**, authenticated (`gh auth status`) - used for checking CI runs
  and creating releases, not just GitHub's web UI.
- **`git`**.

## First-time setup

```bash
cd "concept2-logbook-ha"
python3 -m venv .venv --upgrade-deps   # --upgrade-deps matters: a fresh venv
                                         # on some Python installs has no pip
                                         # otherwise
source .venv/bin/activate
pip install -r requirements_test.txt
```

## Running checks locally (mirrors CI exactly)

```bash
source .venv/bin/activate

# Tests (CI: .github/workflows/test.yml)
pytest tests --cov=custom_components.concept2_logbook

# Lint + format (CI: .github/workflows/lint.yml)
ruff check custom_components tests
ruff format --check custom_components tests
```

All four must pass before pushing. CI also runs `hassfest` (HA's own
integration-quality check) and HACS validation - those have no local
equivalent worth installing; CI is the check for those two.

## Making a change

1. Read `CLAUDE.md` first - binding constraints (C1-C4) and process rules.
   If a change would conflict with any of C1-C4, stop and flag it rather
   than implementing around it.
2. For anything non-trivial, present a plan and get explicit approval before
   writing code (CLAUDE.md process rule #2).
3. Write the code + tests together, not tests-after.
4. Run the full local check suite above before committing.
5. Commit with a conventional-commit message (`feat:`, `fix:`, `docs:`,
   `test:`, `ci:`, `chore:`).

## Releasing

This project tags a release for almost every meaningful change - including
doc-only changes when they need to be visible to HACS/GitHub's "latest
release" resolution (see `docs/RETROSPECTIVE.md`). The shape is always the
same:

```bash
# 1. Bump the version in the manifest
#    custom_components/concept2_logbook/manifest.json -> "version"

# 2. Add a dated entry to CHANGELOG.md under a new version heading,
#    above the previous one, below an empty [Unreleased]

# 3. Verify locally (see above) - all green before committing

# 4. Commit and push to main
git add <files>
git commit -m "..."
git push

# 5. Wait for all 5 CI checks green on that commit before tagging -
#    never tag on a commit whose CI hasn't finished/passed
gh run list --repo kennethnilssen/hacs-concept2-logbook --limit 6

# 6. Tag (annotated, not lightweight) and push the tag
git tag -a vX.Y.Z -F <path-to-a-tag-message-file>
git push origin vX.Y.Z

# 7. Publish the GitHub release (omit --prerelease unless it's genuinely
#    a pre-release - HACS treats non-prerelease as the default update
#    offered to everyone, no "Show beta versions" toggle needed)
gh release create vX.Y.Z --repo kennethnilssen/hacs-concept2-logbook \
  --title "..." --notes-file <path-to-release-notes-file>

# 8. Confirm it's actually live as the latest release
gh api repos/kennethnilssen/hacs-concept2-logbook/releases/latest --jq '.tag_name, .prerelease'
```

**Why a file for the commit/tag message, not `-m "..."` inline:** long
messages containing an apostrophe or contraction reliably break
`git commit -m "$(cat <<'EOF' ... EOF)"` heredoc syntax in this shell setup.
Write the message to a scratch file and use `git commit -F <file>` /
`git tag -a vX.Y.Z -F <file>` instead - it just works, every time.

## Checking CI status

```bash
gh run list --repo kennethnilssen/hacs-concept2-logbook --limit 6
```

Look for `Test`, `Lint`, `Hassfest`, `HACS validation`, and `CodeQL` (the
last runs on a separate `dynamic` trigger, slightly offset from the push
event) all showing `completed success` for the commit in question.

## If HACS doesn't show a new release

This has happened even when the release itself is 100% correctly published
(verified via `gh api .../releases/latest`). It's a HACS-side cache/refresh
timing issue on the Home Assistant instance, not a repo problem. Fix order:

1. HACS -> the integration's page -> **⋮ -> Redownload** (forces HACS to
   re-fetch this repo's data right now).
2. Check HACS's own settings for a GitHub API rate-limit warning.
3. Full Home Assistant restart, as a last resort.

## Common gotchas

- **A fresh `venv` sometimes has no `pip`.** Fixed by `--upgrade-deps` on
  `python3 -m venv` (see First-time setup above).
- **`ruff format` can strip parentheses from a multi-exception
  `except (A, B):` clause**, which then reads like a Python-2-era mistake.
  Restructure to need only one exception type where practical rather than
  fighting the formatter.
- **HACS requires a tagged release to auto-update at all** once a repo has
  more than one commit past its last tag - untagged/commit-based delivery
  uses a GitHub archive URL pattern that reliably 404s.
