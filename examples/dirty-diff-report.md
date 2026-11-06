Diff checked: staged
Lines checked: 4
Findings: 3
- config.py:2 — AWS access key — value `AKIA...ZZZZ`
- config.py:3 — GitHub token — value `ghp_...0000`
- config.py:4 — Password assignment — value `s3cr...1234`
Verdict: STOP — do not commit.
What to do next: Remove the secrets from the diff, move them to a .env file, and rotate any key that was ever pushed.
