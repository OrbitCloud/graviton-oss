#!/usr/bin/env bash
# Post-push hook: surfaces PR link after git push or gh pr create.
# Called by Claude Code as a PostToolUse hook for Bash commands.
# Reads JSON from stdin, returns JSON with additionalContext.
set -euo pipefail

# Require jq for JSON parsing
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Read the hook payload from stdin
input="$(cat)"

# Extract the command that was executed
command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"

# Only act on git push or gh pr create commands.
# Note: gh pr create matching is a convenience enhancement beyond P0 requirements
# (which only specify git push). Kept because it improves PR link visibility.
case "$command" in
  git\ push*|gh\ pr\ create*) ;;
  *) exit 0 ;;
esac

# Check if the tool execution was successful (non-error exit)
exit_code="$(printf '%s' "$input" | jq -r '.tool_response.exitCode // "0"')"
if [ "$exit_code" != "0" ]; then
  exit 0
fi

# Require gh CLI
if ! command -v gh &>/dev/null; then
  exit 0
fi

# Try to get the PR URL for the current branch
pr_url="$(gh pr view --json url -q .url 2>/dev/null || true)"

if [ -n "$pr_url" ]; then
  jq -n --arg url "$pr_url" '{
    additionalContext: ("Pull request: " + $url)
  }'
else
  jq -n '{
    additionalContext: "No pull request found for this branch. Create one with: gh pr create"
  }'
fi
