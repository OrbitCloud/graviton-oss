# Task 03: Post-Push Hook Script

> Status: done

## Goal
Create `.claude/hooks/post-push.sh` that surfaces PR links after git push and gh pr create.

## Acceptance Criteria
- [ ] Script reads JSON from stdin and extracts tool_input.command
- [ ] Only acts on `git push` or `gh pr create` commands
- [ ] Checks for gh CLI availability (exits 0 if missing)
- [ ] Returns JSON with additionalContext containing PR URL
- [ ] Handles no-PR case gracefully
- [ ] Script is executable (chmod +x)
- [ ] Passes `bash -n` syntax check
