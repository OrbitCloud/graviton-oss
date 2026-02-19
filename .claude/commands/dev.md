**ACTION REQUIRED: Spawn a subagent using the Task tool.**

Do NOT implement code directly. Instead, immediately call the Task tool with:

```
Task(
  subagent_type: "general-purpose",
  description: "Developer implementing [feature]",
  prompt: "
    Read and follow the instructions in .claude/agents/dev.md

    Requirements folder: $ARGUMENTS

    Your task:
    1. Read .claude/agents/dev.md for your role and process
    2. Read $ARGUMENTS/README.md for requirements
    3. Check for existing task-NN.md files and review-NN.md files
    4. Create task breakdown if not already done
    5. Implement using TDD (test first, then code, then refactor)
    6. Run: make fmt && make lint && make test
    7. Report what you built when done
  "
)
```

Replace `$ARGUMENTS` with: **$ARGUMENTS**

If `$ARGUMENTS` is empty, ask the user which feature to implement.
