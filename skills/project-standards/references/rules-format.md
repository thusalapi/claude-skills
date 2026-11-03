# Rules file format

`.claude/standards-rules.json` holds the rules a regex can check. The prose skills hold everything else. Run the checker from the repo root:

```bash
python3 check_rules.py                        # whole repo
python3 check_rules.py --changed origin/main  # only files in this branch
```

It exits with 1 when any `error` finding remains, so it can run in CI or a pre-commit hook.

## Shape

```json
{
  "rules": [
    {
      "id": "no-raw-hex",
      "files": ["src/components/**/*.tsx"],
      "exclude": ["src/components/pdf/**"],
      "pattern": "#[0-9a-fA-F]{6}\\b",
      "message": "Use a semantic Tailwind token, never a raw hex colour.",
      "severity": "error"
    }
  ]
}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | yes | Short name shown in findings |
| `files` | yes | Glob list the rule applies to |
| `pattern` | yes | Regex searched line by line |
| `message` | yes | What to do instead |
| `exclude` | no | Globs to skip |
| `severity` | no | `error` (default) fails the run, `warning` only reports |
| `only_if_file_contains` | no | Regex. Apply the rule only to files that contain it (for example `"use client"`) |
| `unless_file_contains` | no | Regex. Skip files that contain it |
| `ignore_lines_matching` | no | Regex. Skip matching lines (for example comments) |
| `ignore_case` | no | `true` for a case-insensitive pattern |

Add `standards-ignore` in a comment on a line to silence it on purpose. Reviewers should question every one.

## Good candidates for rules

- Hard-coded colours, brand names, logo paths or URLs outside the config file
- Banned imports (a UI library you decided against, a server module in client code)
- `float` or `parseFloat` in money code
- Raw SQL outside the data layer
- `console.log` in server code
- Editing applied migrations (rule on the migrations folder plus `--changed`)

Keep rules few and precise. A noisy rule gets ignored, and then all rules get ignored.
