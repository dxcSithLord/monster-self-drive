# Markdown Lint Skill

Use this skill to test markdown files for lint errors and automatically apply
non-breaking fixes.

## Description

This skill provides markdown linting capabilities using markdownlint-cli. It
can:

1. Check markdown files for style and formatting issues
2. Automatically fix non-breaking issues where possible
3. Report remaining issues that need manual attention

## Usage

When invoked, this skill will:

1. Run `markdownlint` on all `.md` files in the project
2. Apply automatic fixes using `markdownlint --fix` where safe
3. Report any remaining issues that require manual intervention

## Commands

### Check All Markdown Files

```bash
markdownlint "**/*.md" --config .markdownlint.json
```

### Fix Automatically Fixable Issues

```bash
markdownlint --fix "**/*.md" --config .markdownlint.json
```

### Check Specific File

```bash
markdownlint <filename.md> --config .markdownlint.json
```

## Configuration

The project uses `.markdownlint.json` for configuration. Current settings:

- Line length: 120 characters (excludes code blocks, tables, and headings)
- MD024 (no duplicate headings): Only checks siblings
- MD033 (no inline HTML): Disabled
- MD036 (no emphasis as heading): Disabled (project uses emphasis for
  sub-headings)
- MD040 (fenced code language): Allows text, bash, python, json, javascript,
  html, css, yaml, markdown, ini, toml, mermaid, shell, sh
- MD041 (first line should be h1): Disabled
- MD060 (table column style): Disabled (project has varied table styles)

## Common Rules

| Rule | Description | Auto-fixable |
|------|-------------|--------------|
| MD001 | Heading levels should increment by one | No |
| MD003 | Heading style consistency | Yes |
| MD009 | No trailing spaces | Yes |
| MD010 | No hard tabs | Yes |
| MD011 | Reversed link syntax | No |
| MD012 | Multiple consecutive blank lines | Yes |
| MD013 | Line length | No |
| MD022 | Headings should be surrounded by blank lines | Yes |
| MD023 | Headings must start at beginning of line | Yes |
| MD031 | Fenced code blocks surrounded by blank lines | Yes |
| MD032 | Lists surrounded by blank lines | Yes |
| MD034 | Bare URLs without angle brackets | Yes |
| MD037 | No spaces inside emphasis markers | Yes |
| MD038 | No spaces inside code span elements | Yes |
| MD047 | Files should end with single newline | Yes |

## Workflow

1. First, run the fix command to apply automatic fixes
2. Then run the check command to see remaining issues
3. Manually fix any issues that cannot be auto-fixed
4. Re-run check to verify all issues are resolved
