#!/usr/bin/env python3
"""Check a codebase against the machine-checkable rules in a standards pack.

Usage (from the repo root):
    python3 check_rules.py                       # all files the rules cover
    python3 check_rules.py --rules path.json     # custom rules file
    python3 check_rules.py --changed origin/main # only files changed since a git ref
    python3 check_rules.py --json                # machine-readable output

Exit code 0 = clean, 1 = findings, 2 = bad rules file. No dependencies beyond Python 3.8.
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

SKIP_DIRS = {".git", "node_modules", ".next", "dist", "build", "coverage", "__pycache__", ".venv", "venv"}


def load_rules(path):
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        sys.exit(f"cannot read rules file {path}: {e}")
    rules = data.get("rules", [])
    for r in rules:
        for key in ("id", "files", "pattern", "message"):
            if key not in r:
                print(f"rule {r.get('id', '?')} is missing '{key}'", file=sys.stderr)
                sys.exit(2)
        flags = re.IGNORECASE if r.get("ignore_case") else 0
        r["_re"] = re.compile(r["pattern"], flags)
        r["_if"] = re.compile(r["only_if_file_contains"]) if r.get("only_if_file_contains") else None
        r["_unless"] = re.compile(r["unless_file_contains"]) if r.get("unless_file_contains") else None
        r["_skip_line"] = re.compile(r["ignore_lines_matching"]) if r.get("ignore_lines_matching") else None
    return rules


def match_any(path, globs):
    # fnmatch's * also crosses "/", so "src/**/*.tsx" and "src/*.tsx" both behave as expected
    return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(path, g.replace("**/", "")) for g in globs)


def walk(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith("_pr-")]
        for f in files:
            yield os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/")


def changed_files(ref):
    out = subprocess.run(["git", "diff", "--name-only", "--diff-filter=ACMR", ref], capture_output=True, text=True, check=True)
    return [x for x in out.stdout.splitlines() if x and os.path.exists(x)]


def check(rules, files):
    findings = []
    for path in files:
        applicable = [r for r in rules if match_any(path, r["files"]) and not match_any(path, r.get("exclude", []))]
        if not applicable:
            continue
        try:
            text = open(path, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        lines = text.splitlines()
        for r in applicable:
            if r["_if"] and not r["_if"].search(text):
                continue
            if r["_unless"] and r["_unless"].search(text):
                continue
            for n, line in enumerate(lines, 1):
                if "standards-ignore" in line or (r["_skip_line"] and r["_skip_line"].search(line)):
                    continue
                m = r["_re"].search(line)
                if m:
                    findings.append({"rule": r["id"], "severity": r.get("severity", "error"), "file": path,
                                     "line": n, "match": m.group(0)[:80], "message": r["message"]})
    return findings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rules", default=".claude/standards-rules.json")
    ap.add_argument("--changed", metavar="REF", help="only check files changed since this git ref")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    rules = load_rules(a.rules)
    files = changed_files(a.changed) if a.changed else list(walk("."))
    findings = check(rules, files)

    if a.json:
        print(json.dumps(findings, indent=2))
    else:
        for f in findings:
            print(f"{f['file']}:{f['line']}  [{f['severity']}] {f['rule']}: {f['message']}  ({f['match']!r})")
        errors = sum(f["severity"] == "error" for f in findings)
        print(f"\n{len(findings)} finding(s), {errors} error(s), {len(rules)} rule(s), {len(files)} file(s) scanned")
    sys.exit(1 if any(f["severity"] == "error" for f in findings) else 0)


if __name__ == "__main__":
    main()
