#!/usr/bin/env bash
echo "Running 01onCreate.sh"

echo "export PATH=$PATH:/sbin:/bin:/usr/bin:/usr/sbin" >> ~vscode/.bashrc

poetry self add poetry-multiproject-plugin
poetry self add poetry-polylith-plugin

cp -r ~/.oh-my-zsh/custom/plugins/zsh-autoswitch-virtualenv ~/.oh-my-zsh/custom/plugins/autoswitch_virtualenv