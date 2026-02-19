# Task 02: Create .github/agents/dev.md

> Status: done

## Goal
Create the Copilot-compatible developer agent definition derived from `.claude/agents/dev.md`.

## Acceptance Criteria
- [ ] File exists at `.github/agents/dev.md`
- [ ] Has YAML frontmatter with `name`, `description`, `tools` (no `model`)
- [ ] Body covers same role as `.claude/agents/dev.md`
- [ ] Header comment notes derivation from `.claude/agents/dev.md`
- [ ] Under 30,000 characters

## Notes
Tools field: `["github", "file_search", "code_search", "run_command", "create_file", "edit_file"]`
