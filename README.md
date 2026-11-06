# secret-scan-skill

Scan a local diff for leaked secrets before you commit.

[![CI](https://github.com/haiderstudio/secret-scan-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/secret-scan-skill/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

When an AI coding agent loads this skill, it checks the diff
about to be committed — and nothing else — for secrets, in
this order:

1. Reads the added lines of `git diff` and `git diff --cached`.
   Only lines the commit would add. No history, no whole repo.
2. Checks each added line against a short, named pattern list:
   AWS access keys, GitHub tokens, private key headers, Stripe
   live keys, Slack tokens, OpenAI-style keys, password and
   secret assignments, and JSON Web Tokens.
3. Skips look-alikes: placeholders (`YOUR_API_KEY_HERE`,
   `EXAMPLE-...`), and names with no value (`os.environ["API_KEY"]`).
4. Writes a short report: file, line, kind, and the value
   redacted to first 4 and last 4 characters. Never the full
   secret. Verdict STOP if anything is found, CLEAR if not.

One finding means STOP — do not commit. The report tells the
user to remove the secret from the diff, move it to a `.env`
file, and rotate it if it was ever pushed.

## What it does NOT do

- It does not scan a whole repo or a git history. That is a
  different job, and Gitleaks and TruffleHog already do it.
- It does not verify whether a found secret is live. It never
  calls a provider and never tests a credential. A match is a
  lead for a human to check, not proof.
- It does not fix, remove, revoke, or rotate anything. It
  reports, and stops. The user does the fixing.
- It does not install any tool. It works with `git diff` and
  the pattern list in the skill file.
- It does not promise a clean repo. A CLEAR verdict means no
  pattern matched in this diff — nothing wider.

## Who it is for

Developers who use an AI coding agent and have seen a key
slip into a commit — or worry one will. This skill is the
check before the commit: one diff, a short list of patterns,
a redacted report, and a plain STOP or CLEAR.

## How this differs from similar tools

Secret scanning is a crowded field, and the big tools own
the wide versions of it. This skill is the narrow one:

- Gitleaks (gitleaks/gitleaks, about 29,000 stars, checked
  Nov 6, 2026) is a Go binary that scans a repo, a folder,
  or a full git history against 200+ rules. This skill
  scans one diff, with 8 named patterns, and installs
  nothing.
- TruffleHog (trufflehog/trufflehog, about 28,000 stars,
  checked Nov 6, 2026) scans history, repos, and images,
  and logs in to providers to check whether a found
  credential is live. This skill never calls a provider
  and never checks history.
- GitGuardian's agent skills teach an agent to use
  ggshield, a commercial scanner, with full-history and
  machine-wide scans. This skill uses no outside tool and
  no account.
- secrets-scan (skills-akaihola/secrets-scan, listed on
  eliteai.tools) runs detect-secrets and secretlint over a
  whole repo and needs uvx and bun installed. This skill
  checks one diff, with no installs.
- Secret Scanning Setup (mcpmarket.com, 2 stars) sets up
  Gitleaks and TruffleHog in GitHub Actions. This skill
  sets nothing up — it checks the diff in front of you.

None of those were copied. The diff-only scope, the 8
patterns, the look-alike guards, the redaction rule, and
both worked examples here are original.

## Install

This skill follows the open Agent Skills format: a folder with a
`SKILL.md` file.

**Claude Code / Codex / Gemini CLI (project level):**

```bash
mkdir -p .agents/skills
cp -r skills/secret-scan-skill .agents/skills/secret-scan-skill
```

## Usage

Give the agent a task that ends in a commit, and tell it to
use this skill first. The agent follows
`skills/secret-scan-skill/SKILL.md`: it reads the staged
and unstaged diff, checks the added lines, and writes a
report. STOP means do not commit. CLEAR means no pattern
matched in this diff.

## Example 1 — a dirty diff, verdict STOP

The diff (from `examples/dirty-diff.patch` — all secrets
in it are fake: repeated characters that can never be a
real key):

```diff
+AWS_KEY = "AKIAZZZZZZZZZZZZZZZZ"
+github_token = "ghp_000000000000000000000000000000000000"
+db_password = "s3cret-p4ssw0rd-1234"
+APP_NAME = "sample-app"
```

The report (full report in `examples/dirty-diff-report.md`):

```markdown
Diff checked: staged
Lines checked: 4
Findings: 3
- config.py:2 — AWS access key — value `AKIA...ZZZZ`
- config.py:3 — GitHub token — value `ghp_...0000`
- config.py:4 — Password assignment — value `s3cr...1234`
Verdict: STOP — do not commit.
What to do next: Remove the secrets from the diff, move them to a .env file, and rotate any key that was ever pushed.
```

No full secret appears anywhere in the report — first 4
characters, `...`, last 4 characters.

## Example 2 — a clean diff, verdict CLEAR

The diff (from `examples/clean-diff.patch`) adds three
small functions to `app.py` and no secret. The report
(full report in `examples/clean-diff-report.md`):

```markdown
Diff checked: staged
Lines checked: 9
Findings: 0
Verdict: CLEAR — no secrets found.
```

## Example 3 — look-alikes, not findings

The diff in `examples/false-positive.patch` has four added
lines, and none of them is a finding:

```text
API_KEY = os.environ["API_KEY"]
api_key = "YOUR_API_KEY_HERE"
example_token = "EXAMPLE-1234-ABCD"
aws_key = "AKIAIOSFODNN7EXAMPLE"
```

A name with no value, two placeholders, and a key-shaped
value that says EXAMPLE. The skill skips all four.

## How it is tested

```bash
python3 tests/test_skill.py
```

The tests check that `SKILL.md` has valid `name` and
`description` frontmatter and the required workflow
sections; that `.gitignore` starts with `.env`; that the
skill's pattern list, applied to the three example diffs,
flags 3 findings in the dirty diff (with the right kinds,
line numbers, and redactions), 0 in the clean diff, and 0
in the look-alike diff; that both reports quoted in this
README are the real files; that the install step copies
the skill to a clean folder; and that a real git
walkthrough — base commit, then a staged dirty change —
flags the same 3 findings. The tests also check that
every secret-shaped value in the repo is one of the known
fake values, and that no full secret appears in any
report. Standard library only — no third-party imports,
so the same command runs on a clean CI runner. No
placeholder text anywhere in the repo.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues and pull requests
are welcome; please keep examples real and checkable, and
never put a real secret in an example, a test, or a report.

## Licence

MIT — see [LICENSE](LICENSE). This is original work. The
related tools named above are listed as related work, not
sources — nothing here was copied from them.
