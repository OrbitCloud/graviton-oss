# Summary: GitHub Copilot Agent Compatibility

## What Was Implemented

Three new files were created to enable the GitHub Copilot coding agent to work with the same
role definitions and project context currently used by Claude Code:

### 1. `.github/copilot-instructions.md` (71 lines)
Repository-level context document covering:
- Project purpose (Graviton CDK, Pulumi-based IaC for Azure, Polylith monorepo)
- Directory structure (`components/`, `bases/`, `docs/`, `test/`, `.claude/`, `.github/agents/`)
- Namespace: `orbitcloud_graviton`
- Validation commands: `make fmt`, `make lint`, `make test`, `make pyright`
- Coding conventions: Python 3.10+, Pydantic v2, `enum.StrEnum`, Ruff, line length 100
- Testing conventions: pytest, Pulumi mocking via `test/conftest.py`
- Workflow: requirements in `docs/requirements/`, dev-then-review cycle
- Note that `.claude/agents/` are the authoritative source-of-truth

### 2. `.github/agents/dev.md` (5,103 characters)
Copilot-compatible developer agent with:
- YAML frontmatter: `name`, `description`, `tools` (no `model` field)
- Full body content from `.claude/agents/dev.md`
- Comment block noting derivation from `.claude/agents/dev.md`

### 3. `.github/agents/reviewer.md` (5,414 characters)
Copilot-compatible reviewer agent with:
- YAML frontmatter: `name`, `description`, `tools` (no `model` field)
- Full body content from `.claude/agents/reviewer.md`
- Comment block noting derivation from `.claude/agents/reviewer.md`

## Tests Added

None -- this is a documentation/configuration task with no Python code.

## Decisions and Trade-offs

- **`model` field omitted** from `.github/agents/` frontmatter per the requirements decision
  log. The org/repo default model will be used, avoiding coupling to a specific model identifier.
- **Body content kept identical** to the `.claude/agents/` source files. The only structural
  changes are in the YAML frontmatter (adapted for Copilot format) and the addition of a
  derivation comment block. This minimizes drift and simplifies future sync.
- **`copilot-instructions.md` kept concise** at 71 lines (well under the ~1,000-line limit and
  the 2-page prose guideline). Detailed role definitions live in the agent files, not here.
- **P2 items deferred**: No `docs/adr/copilot-sync.md` was created. The sync process is
  documented in the comment block at the top of each `.github/agents/` file instead.

## Verification

| Check                              | Result                          |
|------------------------------------|---------------------------------|
| `.claude/` files unchanged         | Confirmed (no diff)             |
| `copilot-instructions.md` lines    | 71 (target: 60-80)             |
| `dev.md` character count           | 5,103 (limit: 30,000)          |
| `reviewer.md` character count      | 5,414 (limit: 30,000)          |

## Issues Encountered

None.

## Suggested Next Steps

- Enable the Copilot coding agent for the repository (GitHub org setting)
- Test by assigning a GitHub issue to the Copilot agent and verifying it picks up the context
- Consider creating `docs/adr/copilot-sync.md` if the manual sync process needs more formalization (P2)
- Address the open question from requirements: whether `copilot-instructions.md` should reference
  the `docs/requirements/` convention so the Copilot agent knows to look there when triggered
  from an issue (currently included as part of the workflow section)
