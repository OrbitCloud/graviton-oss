# Task 03: Create .github/agents/reviewer.md

> Status: done

## Goal
Create the Copilot-compatible reviewer agent definition derived from `.claude/agents/reviewer.md`.

## Acceptance Criteria
- [ ] File exists at `.github/agents/reviewer.md`
- [ ] Has YAML frontmatter with `name`, `description`, `tools` (no `model`)
- [ ] Body covers same role as `.claude/agents/reviewer.md`
- [ ] Header comment notes derivation from `.claude/agents/reviewer.md`
- [ ] Under 30,000 characters

## Notes
Tools field: `["github", "file_search", "code_search", "run_command", "create_file", "edit_file"]`
