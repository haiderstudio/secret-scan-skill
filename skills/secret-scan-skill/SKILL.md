---
name: secret-scan-skill
description: Scan a local diff for leaked secrets before you commit. Use when about to commit, or when a diff adds a key, token, password, or private key. Checks only added lines in the local diff, reports findings with the secret redacted, and stops the commit if anything is found. Local-only, report-only, never sends code anywhere, never deletes anything, never fixes anything itself.
---

# secret-scan-skill

Check the diff before you commit. One job: look at the
lines a commit would add, flag anything that looks like a
secret, and say stop or clear. Nothing leaves the machine.
Nothing is fixed for you. The report is the whole output.

## When to use this skill

Use it when the user asks to:
- Commit, push, or open a pull request, and the diff has
  not been checked yet.
- Check a diff for leaked keys, tokens, passwords, or
  private keys.
- Review staged or unstaged changes before they are
  committed.

## When NOT to use it

- Do not use it to scan a whole repo, a full git history,
  or a folder. This skill checks one diff only — the
  changes about to be committed. A full-history scan is a
  different job, and Gitleaks or TruffleHog already do it.
- Do not use it to verify whether a found secret is live.
  It never calls a provider, never logs in anywhere, and
  never tests a credential. A match is a lead, not proof
  that a key works.
- Do not use it to clean history, revoke a key, or remove
  a secret from a file. It reports. The user does the
  fixing.
- Do not use it on a diff that is already committed and
  pushed. A pushed secret needs rotating, not reporting.
  Say that plainly and stop.

## Workflow

### 1. Get the diff — added lines only

Run both of these, in the repo, and read only the lines
they add:

```bash
git diff
git diff --cached
```

- Read only lines that start with `+`. Ignore lines that
  start with `+++` (file headers) and all removed lines.
- If both commands print nothing, there is no diff. Say
  so and stop: "No changes to check."
- Never run `git log`, `git rev-list`, or any history
  command. Never scan files that are not in the diff.

### 2. Check each added line against the pattern list

Check every added line against these patterns, in this
order. A line that matches a pattern is a finding, unless
step 3 says it is not.

| Kind | Pattern (what it looks like) |
| --- | --- |
| AWS access key | `AKIA` followed by 16 capital letters or digits |
| GitHub token | `ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_`, or `github_pat_` followed by 20 or more letters, digits, or underscores |
| Private key | `-----BEGIN` followed by `PRIVATE KEY-----` |
| Stripe live key | `sk_live_` followed by 16 or more letters or digits |
| Slack token | `xoxb-`, `xoxa-`, `xoxp-`, `xoxr-`, or `xoxs-` followed by 10 or more letters, digits, or hyphens |
| OpenAI-style key | `sk-` followed by 20 or more letters or digits |
| Password or secret assignment | `password`, `passwd`, `pwd`, `secret`, `api_key`, `apikey`, or `access_token`, then `=` or `:`, then a quoted value of 8 or more characters |
| JSON Web Token | `eyJ` then two more dot-separated base64 parts |

What is NOT checked: general high-entropy strings with no
known shape, passwords typed inside a shell command with
no assignment, and secrets already committed in history.
Say so in the report if the user asks for those — they
are outside this skill.

### 3. Skip the look-alikes

A matched line is NOT a finding if any of these is true.
Check this before reporting it:

- The value is a placeholder: it contains `EXAMPLE`,
  `PLACEHOLDER`, `YOUR_`, `CHANGE_ME`, or `xxx`,
  or it is exactly `your-key-here` or `test-key`.
- The value is only a name, not a secret: `os.environ["API_KEY"]`,
  `$API_KEY`, `process.env.API_KEY`, or a bare variable name
  with no value after it.
- The line is in a comment or a docstring that says the
  value is fake, with the word `fake` next to it.

If in doubt, report it. A false alarm the user dismisses
in seconds is cheaper than a real key slipping through.

### 4. Write the report, redacted, then stop

Write the report in this fixed shape, and no other shape:

```markdown
Diff checked: <staged, unstaged, or both>
Lines checked: <number of added lines>
Findings: <number>
- <file>:<line> — <kind> — value `<first 4>...<last 4>`
Verdict: STOP — do not commit. / CLEAR — no secrets found.
What to do next: <one line, only if STOP>
```

Rules for the report:

- Redact every value: first 4 characters, then `...`,
  then the last 4 characters. Never print a full secret
  in the report, in chat, or in a log. Never copy a
  secret into a new file.
- One line per finding: file, line number, kind, redacted
  value. No other detail.
- If there are no findings, the verdict is CLEAR and the
  report is two lines: lines checked, and the verdict.
- If there is even one finding, the verdict is STOP. Say
  "do not commit" in plain words.
- "What to do next" is one line only, and only when the
  verdict is STOP: remove the secret from the diff, move
  it to a `.env` file (which must be gitignored), and if
  it was ever committed or pushed, rotate it — a removed
  line does not un-leak a pushed key.
- Then stop. Do not edit a file, do not remove the secret
  yourself, do not commit, do not push. The report is
  the output.

## Good examples

A dirty diff, 3 findings, verdict STOP (full worked
example: the diff in `examples/dirty-diff.patch`, the
report in `examples/dirty-diff-report.md`):

```markdown
Diff checked: staged
Lines checked: 5
Findings: 3
- config.py:2 — AWS access key — value `AKIA...ZZZZ`
- config.py:3 — GitHub token — value `ghp_...0000`
- config.py:4 — Password assignment — value `s3cr...1234`
Verdict: STOP — do not commit.
What to do next: Remove the secrets from the diff, move them to a .env file, and rotate any key that was ever pushed.
```

A clean diff, no findings, verdict CLEAR (full worked
example: `examples/clean-diff.patch` and
`examples/clean-diff-report.md`):

```markdown
Diff checked: staged
Lines checked: 8
Findings: 0
Verdict: CLEAR — no secrets found.
```

Look-alike lines that are skipped, not reported (full
example in `examples/false-positive.patch`):

```text
API_KEY = os.environ["API_KEY"]
api_key = "YOUR_API_KEY_HERE"
example_token = "EXAMPLE-1234-ABCD"
```

The first is a name with no value, the second is a
placeholder, the third is an example value. None of
them is a finding.

## Bad examples (do not write like this)

> Finds a key and prints the whole key in the report.

A full secret in a report is a second leak. Redact it:
first 4, `...`, last 4. Always.

> Finds a key, removes the line, and commits anyway.

Removing the line does not make the key safe if it was
ever pushed, and the skill never edits a file. Report,
say STOP, and let the user fix it.

> Scans the whole git history to be thorough.

That is not this job. The diff is the job. History
scanning is Gitleaks or TruffleHog, with their own
rules and their own install.

> Reports CLEAR after checking only the file names.

File names are not the check. Added lines are the
check. A CLEAR verdict means every added line was
checked against the pattern list.

> Finds nothing and says "the repo has no secrets".

The skill checked one diff, not the repo. A CLEAR
verdict means no pattern matched in this diff. Say
exactly that, nothing wider.

## Output rules

- Output one report per diff, in its own code block.
- Every finding traces to one added line in the diff.
  If it cannot be traced, leave it out.
- Never print a full secret — in the report, in chat,
  or in a log. First 4, `...`, last 4.
- Never claim a check was run that was not run. If
  only the staged diff was checked, say staged only.
- Never say a secret is live, dead, or safe. The skill
  never tests a credential, so it cannot know.
- Never say the repo is clean. Say the diff is clear,
  and only the diff.

## Limits and safety rules

- This skill reads one diff, on this machine only. It
  sends nothing anywhere, needs no API key, and installs
  no tool. It works with `git diff` and the pattern list
  in this file.
- It never edits, deletes, moves, or commits a file. It
  never revokes or rotates a key. It reports, and stops.
- It checks patterns only. A secret in a shape the list
  does not name will not be found. A CLEAR verdict is
  not a promise that no secret exists.
- It never verifies a credential against a provider.
  A match is a lead for a human to check, not proof.
- If a real secret is found, the user must rotate it if
  it was ever committed or pushed. Removing the line
  from the diff is not enough.
- All secrets in this repo's examples and tests are fake:
  repeated characters that can never be a real key.
  Never put a real secret in an example, a test, or a
  report.
