#!/usr/bin/env bash
echo "Running 03postCreate.sh"

# Workaround until it will be possible to auto open a workspace file
# when the devcontainer is created
# https://github.com/microsoft/vscode-remote-release/issues/3665
printf "source /workspaces/.devcontainer/bashrc.sh\n" >> ~/.zshrc