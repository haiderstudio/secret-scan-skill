"""Tests for the secret-scan-skill: frontmatter, required sections,
.gitignore, the skill's pattern list applied to the three example
diffs (dirty flags 3 with redaction, clean flags 0, look-alikes
flag 0), the reports matching the README, a real git walkthrough
on a temp repo, and no real secrets anywhere in the repo.
Standard library only — no third-party imports (a clean CI
runner does not have them)."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "secret-scan-skill" / "SKILL.md"
README = ROOT / "README.md"
DIRTY = ROOT / "examples" / "dirty-diff.patch"
DIRTY_REPORT = ROOT / "examples" / "dirty-diff-report.md"
CLEAN = ROOT / "examples" / "clean-diff.patch"
CLEAN_REPORT = ROOT / "examples" / "clean-diff-report.md"
FALSE_POS = ROOT / "examples" / "false-positive.patch"
GITIGNORE = ROOT / ".gitignore"
CI = ROOT / ".github" / "workflows" / "ci.yml"
BANNED = ["TODO", "FIXME", "lorem", "coming soon"]
# The only secret-shaped values allowed anywhere in this repo.
# All are fake by construction: repeated characters, or an
# EXAMPLE value that the skill's own guard list skips.
FAKE_VALUES = {
    "AKIAZZZZZZZZZZZZZZZZ",
    "ghp_000000000000000000000000000000000000",
    "s3cret-p4ssw0rd-1234",
    "AKIAIOSFODNN7EXAMPLE",
}
GUARD_WORDS = ["EXAMPLE", "PLACEHOLDER", "YOUR_", "CHANGE_ME", "xxx"]

# The skill's pattern list, written out exactly as SKILL.md
# documents it. Order matters: private key first, then the
# provider patterns, then the assignment pattern.
PATTERNS = [
    ("Private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub token",
     re.compile(r"(?:ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)[A-Za-z0-9_]{20,}")),
    ("Stripe live key", re.compile(r"sk_live_[A-Za-z0-9]{16,}")),
    ("Slack token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("OpenAI-style key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("Password assignment", re.compile(
        r"(?i)(password|passwd|pwd|secret|api_key|apikey|access_token)"
        r"\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
    ("JSON Web Token",
     re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")),
]


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        sys.exit(1)


def redact(value):
    return value[:4] + "..." + value[-4:]


def added_lines(patch_path):
    """Return [(new-file line number, line text)] for added lines."""
    out = []
    new_no = 0
    for raw in patch_path.read_text().splitlines():
        m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
        if m:
            new_no = int(m.group(1))
            continue
        if raw.startswith("+++") or raw.startswith("---"):
            continue
        if raw.startswith("+"):
            out.append((new_no, raw[1:]))
            new_no += 1
        elif raw.startswith("-"):
            continue
        else:
            new_no += 1
    return out


def scan_added(patch_path):
    """Apply the skill's patterns + look-alike guards to a diff.

    Returns (lines_checked, findings) where each finding is
    (line number, kind, redacted value)."""
    findings = []
    lines = added_lines(patch_path)
    for lineno, line in lines:
        for kind, pattern in PATTERNS:
            m = pattern.search(line)
            if not m:
                continue
            value = m.group(0)
            if kind == "Password assignment":
                value = re.search(r"['\"]([^'\"]+)['\"]", line).group(1)
            # Look-alike guards from SKILL.md step 3.
            if any(w in value for w in GUARD_WORDS):
                break
            if ("os.environ" in line or "process.env" in line
                    or re.search(r"\$\w+", line)):
                break
            findings.append((lineno, kind, redact(value)))
            break
    return len(lines), findings


def main():
    skill = SKILL.read_text()
    m = re.match(r"---\n(.*?)\n---\n", skill, re.S)
    check("test_skill_frontmatter",
          bool(m) and "name: secret-scan-skill" in m.group(1)
          and "description:" in m.group(1))
    for section in ["When to use this skill", "When NOT to use it",
                    "Workflow", "Good examples", "Bad examples",
                    "Output rules", "Limits and safety rules"]:
        check("test_skill_sections_" + section.split()[0], section in skill)
    check("test_skill_no_yaml_import", "import yaml" not in skill)
    check("test_gitignore_env_first",
          GITIGNORE.read_text().splitlines()[0] == ".env")
    for f in [SKILL, README, DIRTY, DIRTY_REPORT, CLEAN, CLEAN_REPORT,
              FALSE_POS]:
        check("test_no_placeholders_" + f.name,
              not any(b in f.read_text() for b in BANNED))

    # Dirty diff: 4 added lines, 3 findings, redacted, STOP.
    n, findings = scan_added(DIRTY)
    check("test_dirty_lines_checked", n == 4)
    check("test_dirty_finding_count", len(findings) == 3)
    check("test_dirty_kinds",
          [k for _, k, _ in findings]
          == ["AWS access key", "GitHub token", "Password assignment"])
    check("test_dirty_line_numbers",
          [n for n, _, _ in findings] == [2, 3, 4])
    check("test_dirty_redacted",
          [v for _, _, v in findings]
          == ["AKIA...ZZZZ", "ghp_...0000", "s3cr...1234"])
    report = DIRTY_REPORT.read_text()
    check("test_dirty_report_lines", "Lines checked: 4" in report)
    check("test_dirty_report_findings", "Findings: 3" in report)
    check("test_dirty_report_stop", "Verdict: STOP" in report)
    for _, _, redacted in findings:
        check("test_dirty_report_has_" + redacted[:4], redacted in report)
    for fake in FAKE_VALUES:
        check("test_dirty_report_no_full_secret_" + fake[:4],
              fake not in report)

    # Clean diff: 9 added lines, 0 findings, CLEAR.
    n, findings = scan_added(CLEAN)
    check("test_clean_lines_checked", n == 9)
    check("test_clean_no_findings", findings == [])
    clean_report = CLEAN_REPORT.read_text()
    check("test_clean_report_lines", "Lines checked: 9" in clean_report)
    check("test_clean_report_clear", "Verdict: CLEAR" in clean_report)

    # Look-alikes: 4 added lines, 0 findings — the guards work.
    n, findings = scan_added(FALSE_POS)
    check("test_false_positive_lines", n == 4)
    check("test_false_positive_none", findings == [])

    # The reports quoted in the README are the real files.
    readme = README.read_text()
    check("test_dirty_report_in_readme",
          report.strip() in readme)
    check("test_clean_report_in_readme",
          clean_report.strip() in readme)

    # CI is valid plain YAML shape and runs only stdlib tests.
    ci = CI.read_text()
    check("test_ci_valid",
          "python3 tests/test_skill.py" in ci
          and "actions/checkout@v4" in ci
          and "runs-on: ubuntu-latest" in ci)
    check("test_ci_no_pip_install", "pip install" not in ci)

    # No real secrets anywhere: every secret-shaped value in the
    # repo must be one of the known fakes, and no .env file exists.
    check("test_no_env_file", not (ROOT / ".env").exists())
    found = set()
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix in (".md", ".py", ".patch", ".yml"):
            text = path.read_text(errors="ignore")
            for pat in (r"AKIA[0-9A-Z]{16}",
                        r"(?:ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)[A-Za-z0-9_]{20,}",
                        r"sk_live_[A-Za-z0-9]{16,}"):
                found.update(re.findall(pat, text))
    check("test_only_fake_secrets", found <= FAKE_VALUES)

    # Install step from the README works on a clean folder.
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / ".agents" / "skills"
        dest.mkdir(parents=True)
        shutil.copytree(ROOT / "skills" / "secret-scan-skill",
                        dest / "secret-scan-skill")
        check("test_install_copies_skill",
              (dest / "secret-scan-skill" / "SKILL.md").exists())

    # Walkthrough on a real git repo: base commit, then a staged
    # dirty change with the same fake values. The skill's steps
    # (git diff --cached, added lines, patterns) must flag 3.
    with tempfile.TemporaryDirectory() as tmp:
        run = lambda *args: subprocess.run(
            ["git", *args], cwd=tmp, capture_output=True, text=True,
            check=True)
        run("init", "-q")
        run("config", "user.email", "test@example.com")
        run("config", "user.name", "Test")
        (Path(tmp) / "config.py").write_text("import os\n\n\ndef connect():\n")
        run("add", "config.py")
        run("commit", "-qm", "base")
        (Path(tmp) / "config.py").write_text(
            'import os\n'
            'AWS_KEY = "AKIAZZZZZZZZZZZZZZZZ"\n'
            'github_token = "ghp_000000000000000000000000000000000000"\n'
            'db_password = "s3cret-p4ssw0rd-1234"\n'
            'APP_NAME = "sample-app"\n'
            '\n'
            'def connect():\n')
        run("add", "config.py")
        diff = subprocess.run(["git", "diff", "--cached"], cwd=tmp,
                              capture_output=True, text=True,
                              check=True).stdout
        diff_path = Path(tmp) / "walkthrough.patch"
        diff_path.write_text(diff)
        n, findings = scan_added(diff_path)
        check("test_walkthrough_lines", n == 4)
        check("test_walkthrough_findings", len(findings) == 3)
        check("test_walkthrough_kinds",
              [k for _, k, _ in findings]
              == ["AWS access key", "GitHub token", "Password assignment"])
        # The report built from these findings must not contain a
        # full fake value — only the redacted form.
        built_report = "\n".join(
            f"- {k} — value `{v}`" for _, k, v in findings)
        check("test_walkthrough_report_redacted",
              not any(f in built_report for f in FAKE_VALUES))
    print("All tests passed.")


if __name__ == "__main__":
    main()
