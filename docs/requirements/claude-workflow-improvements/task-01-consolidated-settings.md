# Task 01: Consolidated Permission Allowlist

> Status: done

## Goal
Merge settings.json and settings.local.json into a single settings.json with all required permission categories, using current syntax.

## Acceptance Criteria
- [ ] All allowlist categories from requirements are present
- [ ] Uses `Bash(cmd *)` syntax (not deprecated `Bash(cmd:*)`)
- [ ] PostToolUse hook config is included
- [ ] JSON is valid (`python -m json.tool`)

## Notes
Categories: read-only shell, version/help, git read, git write, build/test, gh CLI, web access, MCP tools.
