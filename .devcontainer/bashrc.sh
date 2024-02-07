#!/usr/bin/env bash

open_workspace() {
    local workspace_file=/workspaces/.vscode/graviton.code-workspace

    if ! [ -f "$workspace_file" ]; then
        echo "🔴 Missing workspace file"
        return 1
    fi

    echo "💬 Opening workspace"
    if code -r "$workspace_file"; then
        echo "🟢 Workspace opened"
        return 0
    fi

    echo "🔴 Failed to open workspace"
    return 1
}
open_workspace
