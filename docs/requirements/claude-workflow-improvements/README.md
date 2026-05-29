# Claude Workflow Improvements Requirements

## Overview
Improve the Claude Code developer experience for the Graviton CDK project by consolidating permission allowlists, adding MCP servers for documentation access, and implementing a post-push hook for PR link visibility.

## Goals
- Reduce permission prompts for safe, routine commands
- Provide in-context documentation access for Azure, Pulumi, and library APIs
- Automatically surface PR links after every `git push`
- Consolidate all settings into a single, committed project-level file

## User Stories
- As a developer, I want safe commands to execute without permission prompts so that my workflow is uninterrupted.
- As a developer, I want to query Azure, Pulumi, and library docs from within Claude Code so that I don't context-switch to a browser.
- As a developer, I want to see the PR link after every push so that I can quickly navigate to it for review.

## Functional Requirements

### Must Have (P0)

#### 1. Consolidated Permission Allowlist
- [ ] Merge `settings.local.json` allows into `settings.json` (project-level, committed)
- [ ] Delete `settings.local.json` (no longer needed)
- [ ] Use current syntax (`Bash(cmd *)`) not deprecated (`Bash(cmd:*)`)
- [ ] Allowlist categories:
  - **Read-only shell utilities**: `cat`, `ls`, `find`, `head`, `tail`, `wc`, `grep`, `echo`, `pwd`, `which`, `test`, `sort`, `uniq`, `diff`, `tr`, `cut`, `basename`, `dirname`, `realpath`
  - **Version/help queries**: `* --version`, `* --help`
  - **Git read operations**: `status`, `diff`, `log`, `merge-base`, `show`, `rev-parse`, `branch --list`
  - **Git write operations**: `checkout`, `checkout -b`, `add`, `commit`, `stash`, `branch`, `fetch`, `switch`, `push`
  - **Build/test tooling**: `make *` (all make targets), `poetry run *`
  - **GitHub CLI**: `gh pr *`, `gh issue *`, `gh gist *`, `gh api *`, `gh run *`
  - **Web access**: `WebSearch`, `WebFetch` for GitHub domains, `learn.microsoft.com`, `pulumi.com`
  - **MCP tools**: `mcp__context7__*`, `mcp__fetch__*`

#### 2. MCP Server Configuration
- [ ] Create `.mcp.json` at project root (committed to repo)
- [ ] Add **Context7** MCP server for library/framework documentation
  ```json
  "context7": {
    "command": "npx",
    "args": ["-y", "@upstash/context7-mcp@latest"]
  }
  ```
- [ ] Add **Fetch** MCP server for ad-hoc URL documentation fetching
  ```json
  "fetch": {
    "command": "uvx",
    "args": ["mcp-server-fetch"]
  }
  ```

#### 3. Post-Push Hook for PR Links
- [ ] Add a `PostToolUse` hook in `settings.json` matching `Bash` commands
- [ ] Create hook script at `.claude/hooks/post-push.sh`
- [ ] Script reads stdin JSON, extracts `tool_input.command`
- [ ] Only acts on commands matching `git push`
- [ ] Uses `gh pr view --json url -q .url` to get PR URL for current branch
- [ ] Returns JSON with `additionalContext` containing the PR link so Claude surfaces it
- [ ] Handles case where no PR exists (silent no-op or suggests creating one)

### Should Have (P1)
- [ ] Add CLAUDE.md with project conventions and workflow guidance
  - Always show PR link after push
  - Use `make` targets for build/test/lint
  - Project structure overview (polylith, components, bases)

### Nice to Have (P2)
- [ ] Brave Search MCP server (requires API key via env var)

## Non-Functional Requirements
- **Portability**: All config committed to repo; works for any team member with `npx`/`uvx` available
- **Security**: No secrets in committed files; env var expansion (`${VAR}`) for any API keys
- **Backwards Compatibility**: No breaking changes; existing workflows continue to work
- **Performance**: Hook script should complete in < 2 seconds

## Edge Cases & Error Handling
| Scenario | Expected Behavior |
|----------|-------------------|
| `git push` to a branch with no PR | Hook silently exits or returns "No PR found — create one with `gh pr create`" |
| `gh` CLI not installed | Hook exits 0 silently (no error shown to user) |
| MCP server binary not available (`npx`/`uvx` missing) | Claude Code shows connection error on startup; does not block usage |
| Hook script times out | Claude Code kills after timeout (default 30s); no impact on push |
| Push fails (non-zero exit) | `PostToolUse` still fires; script should check `tool_response` for errors and skip |

## Affected Files
| File | Action |
|------|--------|
| `.claude/settings.json` | **Modify** — consolidated allowlist + hooks config |
| `.claude/settings.local.json` | **Delete** — merged into settings.json |
| `.claude/hooks/post-push.sh` | **Create** — post-push PR link script |
| `.mcp.json` | **Create** — MCP server configuration |
| `CLAUDE.md` | **Create** (P1) — project conventions |

## Out of Scope
- User-level (`~/.claude/settings.json`) changes — each developer manages their own
- CI/CD integration or GitHub Actions changes
- Pre-commit hook modifications
- Pulumi-specific MCP server (not yet available; Context7 covers Pulumi docs)

## Dependencies
- `gh` CLI installed and authenticated (for post-push hook)
- `npx` available (for Context7 MCP)
- `uvx` available (for Fetch MCP)
- Node.js runtime (for npx)
- `jq` installed (for hook script JSON parsing)

## Open Questions
- [ ] Should `git push` require confirmation (deny list) or be auto-allowed? Currently proposed as **allowed** for smooth workflow — confirm with user.
- [ ] Should the hook also fire after `gh pr create` to print the new PR link?

## Acceptance Criteria
- Running `make test`, `make lint`, `poetry run pytest` execute without permission prompts
- Git operations (status, diff, log, checkout, add, commit, push) execute without prompts
- `context7` and `fetch` MCP servers connect on Claude Code startup (visible in `/mcp`)
- After `git push`, Claude automatically shows the PR URL in its response
- All configuration is in committed files (no `.local.json` needed)
- No secrets are stored in committed files
