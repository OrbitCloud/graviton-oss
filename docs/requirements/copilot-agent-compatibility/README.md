# GitHub Copilot Agent Compatibility Requirements

## Overview

The `.claude/` directory defines a structured AI agent workflow for this repository (developer agent,
reviewer agent, and orchestration commands). This feature makes that structure also usable by the
**GitHub Copilot coding agent** — the agent triggered from GitHub issues on github.com.

The `.claude/` directory remains the **source of truth**. Copilot-compatible files are derived from
it when there is no shared format.

## Goals

- Enable GitHub Copilot coding agent to run `dev` and `reviewer` sessions with the same role
  definitions currently used by Claude Code
- Provide the coding agent with repository-level context (architecture, conventions, validation
  commands) via `.github/copilot-instructions.md`
- Keep the maintenance burden low: `.claude/agents/` is authoritative; Copilot files are derived
  and noted as such

## User Stories

As a maintainer, I want to assign a GitHub issue to the Copilot coding agent so that it uses the
same developer role definition (TDD, clean code, Pulumi patterns) as when I run `/dev-cycle`
locally with Claude Code.

As a maintainer, I want the Copilot coding agent to know the project's architecture, toolchain, and
validation commands without having to embed that context in every issue description.

## Functional Requirements

### Must Have (P0)

- [ ] `.github/copilot-instructions.md` exists and contains:
  - Project purpose (Graviton CDK — Pulumi-based IaC for Azure, Polylith monorepo)
  - Directory structure overview (`components/`, `bases/`, `docs/`, `test/`)
  - Toolchain and validation commands (`make fmt`, `make lint`, `make test`, `make pyright`)
  - Coding conventions (Python 3.10+, Pydantic v2, `enum.StrEnum`, type hints, Ruff, line length 100)
  - Testing conventions (pytest, Pulumi mocking via `test/conftest.py`)
  - Namespace (`orbitcloud_graviton`)
  - A note that `.claude/agents/` are the source-of-truth agent definitions

- [ ] `.github/agents/dev.md` exists with:
  - Copilot-compatible YAML frontmatter (`name`, `description`, `model`, `tools`)
  - Body content that covers the same role as `.claude/agents/dev.md`:
    TDD workflow (red/green/refactor), task file protocol, validation sequence, final report format
  - A header comment noting this file is derived from `.claude/agents/dev.md`

- [ ] `.github/agents/reviewer.md` exists with:
  - Copilot-compatible YAML frontmatter (`name`, `description`, `model`, `tools`)
  - Body content that covers the same role as `.claude/agents/reviewer.md`:
    review checklist (correctness, Python standards, edge cases, security, Pulumi patterns, tests),
    feedback format (Critical / Important / Suggestions / Praise), review file protocol
  - A header comment noting this file is derived from `.claude/agents/reviewer.md`

### Should Have (P1)

- [ ] A comment block at the top of each `.github/agents/` file explains:
  - Which `.claude/agents/` file is the source of truth
  - What was changed to adapt it for Copilot frontmatter

- [ ] `.github/copilot-instructions.md` stays within the 2-page / ~1,000-line guideline (it should
  be well under this limit)

### Nice to Have (P2)

- [ ] A `docs/adr/copilot-sync.md` or comment in `.claude/` noting the sync process: when
  `.claude/agents/dev.md` or `reviewer.md` change significantly, `.github/agents/` counterparts
  should be updated manually
- [ ] The `analyst` command's role description is mentioned in `copilot-instructions.md` as a
  workflow guide, so a Copilot session understands the requirements → dev → review cycle even
  though `/analyst` is not available as a command

## Non-Functional Requirements

- **Backwards Compatibility:** Existing `.claude/` files are unchanged. No Claude Code behaviour is
  altered.
- **Size Constraint:** `.github/copilot-instructions.md` must not exceed 2 pages of prose (GitHub
  guideline). Agent files must not exceed 30,000 characters each (GitHub limit).
- **Maintainability:** Files are clearly marked as derived. The sync process requires no tooling —
  it is a manual copy-and-adapt step documented by comments.

## Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| `.claude/agents/dev.md` body is updated | Maintainer manually mirrors changes to `.github/agents/dev.md` body |
| Agent file exceeds 30,000 char limit | Trim Nice-to-Have sections; `.claude/` retains full content |
| `.github/copilot-instructions.md` exceeds 2-page guideline | Trim to essentials; move elaboration to agent files |

## Affected Files

**New files (to create):**
- `.github/copilot-instructions.md`
- `.github/agents/dev.md`
- `.github/agents/reviewer.md`

**Unchanged (source of truth):**
- `.claude/agents/dev.md`
- `.claude/agents/reviewer.md`
- `.claude/commands/`
- `.claude/settings.json`

## Out of Scope

- Mirroring `.claude/commands/` (no Copilot equivalent for slash commands)
- Automating sync between `.claude/agents/` and `.github/agents/` (manual process)
- VS Code Copilot chat configuration (this targets the coding agent on github.com only)
- MCP server configuration for Copilot agents

## Dependencies

- GitHub Copilot coding agent must be enabled for the repository (GitHub org setting)
- No code dependencies — this is purely documentation/configuration files

## Open Questions

- [ ] Should `.github/copilot-instructions.md` reference the `docs/requirements/` convention so the
  Copilot coding agent knows to look there when triggered from an issue?

## Decisions Made

- **`model` field in `.github/agents/` frontmatter:** Omitted — the org/repo default model will be
  used. This avoids coupling the agent definitions to a specific model identifier.

## Acceptance Criteria

- [ ] A GitHub issue assigned to the Copilot coding agent results in a session that understands the
  Polylith structure, uses TDD, and runs `make fmt && make lint && make test` as its validation sequence
- [ ] The Copilot `dev` agent file contains all key role behaviours from `.claude/agents/dev.md`
  (TDD steps, task file protocol, validation commands, final SUMMARY.md)
- [ ] The Copilot `reviewer` agent file contains all key review criteria from
  `.claude/agents/reviewer.md` (8 checklist categories, feedback format, verdict options)
- [ ] `git grep` confirms no `.claude/` files were modified
- [ ] All new files are under their respective size limits
