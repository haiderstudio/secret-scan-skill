# Contributing

Small, focused improvements are welcome.

- Open an issue first for anything larger than a typo or a clearer example, so the scope can be agreed before work starts.
- Never weaken the safety rules: the skill must check the diff only, must redact every value, must never print a full secret, must never edit or commit a file, and must never send code anywhere.
- Every claim in a proposed change must be verifiable: a command must be runnable, a pattern must match a real example, a report line must trace to an added line in a diff.
- Run `python3 tests/test_skill.py` before opening a pull request. It must pass.
- Do not add placeholder text, invented features, or copied content without attribution.
- Python standard library only — no new dependency without a reason in the issue.
- Never put a real secret in an example, a test, or a report. Test data uses fake values only: repeated characters that can never be a real key.
