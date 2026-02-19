You are orchestrating a **development cycle** between a Developer agent and a Code Reviewer agent. Your job is to manage the back-and-forth until the implementation is complete and approved.

## The Cycle

```
┌─────────────────┐
│   Requirements  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Developer    │◄─────────┐
│   Implements    │          │
└────────┬────────┘          │
         │                   │
         ▼                   │
┌─────────────────┐          │
│    Reviewer     │          │
│    Critiques    │          │
└────────┬────────┘          │
         │                   │
         ▼                   │
    ┌─────────┐              │
    │Approved?│──── No ──────┘
    └────┬────┘
         │ Yes
         ▼
┌─────────────────┐
│      Done       │
└─────────────────┘
```

## Agent Instructions

- Developer: `.claude/agents/dev.md`
- Reviewer: `.claude/agents/reviewer.md`

## Your Process

### Phase 1: Setup
1. Read the requirements from: **$ARGUMENTS/README.md**
2. Understand what needs to be built
3. **Create feature branch** (if not already on one):
   ```bash
   git checkout -b feature/[feature-name]
   ```
4. Review any existing task files and review files in **$ARGUMENTS/**

### Phase 2: Development Loop

**For each iteration:**

1. **Invoke Developer Agent**
   Use the Task tool:
   ```
   Task(
     subagent_type: "general-purpose",
     description: "Developer implementing [feature]",
     prompt: "
       Read and follow .claude/agents/dev.md

       Requirements folder: $ARGUMENTS
       Previous reviewer feedback: [paste feedback if any, or 'None - first iteration']

       Implement the next increment using TDD.
       Run: make fmt && make lint && make test
       Report what you built when done.
     "
   )
   ```

2. **Invoke Reviewer Agent**
   Use the Task tool:
   ```
   Task(
     subagent_type: "general-purpose",
     description: "Reviewer checking [feature]",
     prompt: "
       Read and follow .claude/agents/reviewer.md

       Requirements folder: $ARGUMENTS

       Review the branch changes (git diff main...HEAD).
       Provide structured feedback with verdict: APPROVE or REQUEST CHANGES
     "
   )
   ```

3. **Evaluate**
   - Read the latest `$ARGUMENTS/review-NN.md` for the verdict
   - If APPROVE: Check for non-critical suggestions
     - If there are suggestions, send back to developer to evaluate
     - Otherwise move to Finalization
   - If REQUEST CHANGES: Loop back to developer (they'll read the review file)

### Phase 3: Finalization
1. Run final validation: `make fmt && make lint && make test && make pyright`
2. Summarize what was built
3. Suggest a conventional commit message (e.g., `feat(ComponentName): Add capability`)

## Iteration Limits

- Maximum 5 iterations before escalating to user
- If stuck in a loop, ask for human guidance

## Communication

After each iteration, report to the user:
- What the developer implemented
- What the reviewer found
- Current status (continuing / approved / needs help)

## Your Task

Begin the development cycle for: **$ARGUMENTS**

`$ARGUMENTS` should be a path to a requirements folder (e.g., `docs/requirements/feature-name`).

**Start immediately by:**
1. Reading `$ARGUMENTS/README.md` for requirements
2. Checking for existing task/review files in `$ARGUMENTS/`
3. Creating feature branch: `git checkout -b feature/[name]`
4. **Spawning the developer subagent using the Task tool** (do not implement directly - delegate to subagent)

**IMPORTANT:** You are the orchestrator. You MUST use the Task tool to spawn developer and reviewer subagents. Do not implement or review code yourself - delegate to the specialized agents.
