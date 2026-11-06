# Security Policy

This skill reads one local diff (`git diff` and `git diff --cached`). It sends nothing anywhere, edits no file, writes no code, installs no tool, and needs no API key or secret. It never deletes, moves, commits, or pushes anything, and never tests a credential against a provider.

If you find a case where it could do otherwise, please open an issue describing the exact diff and input. Do not include any real secret in the report.

If a real secret was committed or pushed, remove the line and rotate the secret — removing the line alone does not un-leak it.
