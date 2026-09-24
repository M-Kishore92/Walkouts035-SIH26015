"""
Vocabulary Linter — Ethics and Language Compliance Scanner.

Scans the entire codebase for forbidden accusatory, judgmental, or legally
problematic language. CI fails if any violation is found.

Banned words/phrases (case-insensitive):
  - "fraud", "fraudulent" → too accusatory; use "requires field verification"
  - "fake", "forged", "fabricated" → accusatory without legal basis
  - "corrupt" (as in data corruption) → use "data integrity issue"
  - "cheat", "cheating" → accusatory
  - "illegal" → legal determination; use "non-compliant"
  - "conclusive proof" → overstates certainty; use "corroborated evidence"

Permitted alternatives are documented in docs/VOCABULARY_GUIDE.md.

Exit codes:
  0 = clean
  1 = violations found (CI should fail)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Force UTF-8 on Windows consoles to prevent charmap encode errors with emojis
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ── Configuration ─────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent

SCAN_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".yaml", ".yml", ".md", ".html"}

EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".mypy_cache", ".ruff_cache", "dist", "build",
    # Exclude this file and the docs about banned words themselves
}

# Exclude files that may legitimately quote banned terms for documentation
EXCLUDE_FILES = {
    "vocabulary_lint.py",
    "VOCABULARY_GUIDE.md",
    "CHEAT_CARD.md",   # Pitch Q&A may quote what we DON'T say
}

BANNED_PATTERNS: list[tuple[str, str]] = [
    # Pattern, Suggested alternative
    (r"\bfraud(?:ulent)?\b", "Banned: 'fraud/fraudulent' → use 'requires field verification'"),
    (r"\bfak(?:e|ed|ing)\b", "Banned: 'fake/faked/faking' → use 'unverified' or 'flagged mismatch'"),
    (r"\bforg(?:ed|ery)\b", "Banned: 'forged/forgery' → use 'data integrity concern'"),
    (r"\bfabricat(?:ed|ion)\b", "Banned: 'fabricated/fabrication' → use 'unverifiable claim'"),
    (r"\bcorrupt\b(?!ion)", "Banned: 'corrupt' (as adjective about people) → use 'non-compliant'"),
    (r"\bcheat(?:ing|er)?\b", "Banned: 'cheat/cheating/cheater' → use 'discrepancy requiring verification'"),
    (r"\billegal\b", "Banned: 'illegal' (legal determination) → use 'non-compliant' or 'irregular'"),
    (r"\bconclusive\s+proof\b", "Banned: 'conclusive proof' (overstates certainty) → use 'corroborated evidence'"),
    (r"\b100%\s+certain\b", "Banned: '100% certain' → use confidence intervals"),
    (r"\bproven\s+(?:fraud|guilt)\b", "Banned: 'proven fraud/guilt' → legal determination"),
]


def scan_file(path: Path, patterns: list[tuple[re.Pattern, str]]) -> list[dict]:
    """Scan one file for banned vocabulary. Returns list of violation dicts."""
    violations = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, PermissionError):
        return []

    for line_num, line in enumerate(content.splitlines(), start=1):
        for pattern, message in patterns:
            if pattern.search(line.lower()):
                violations.append({
                    "file": str(path.relative_to(REPO_ROOT)),
                    "line": line_num,
                    "text": line.strip()[:120],
                    "violation": message,
                })
    return violations


def main() -> int:
    compiled = [
        (re.compile(pat, re.IGNORECASE), msg)
        for pat, msg in BANNED_PATTERNS
    ]

    all_violations = []
    files_scanned = 0

    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in SCAN_EXTENSIONS:
            continue
        if path.name in EXCLUDE_FILES:
            continue
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue

        violations = scan_file(path, compiled)
        all_violations.extend(violations)
        files_scanned += 1

    print(f"\n🔍 Vocabulary Lint — Scanned {files_scanned} files")
    print("=" * 60)

    if not all_violations:
        print("✅  PASS — No banned vocabulary found.")
        print("   The codebase uses respectful, non-accusatory language throughout.")
        return 0

    print(f"❌  FAIL — {len(all_violations)} violation(s) found:\n")
    for v in all_violations:
        print(f"  {v['file']}:{v['line']}")
        print(f"    Text:      {v['text']}")
        print(f"    Violation: {v['violation']}")
        print()

    print("Fix: Replace banned terms with approved alternatives (see docs/VOCABULARY_GUIDE.md).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
