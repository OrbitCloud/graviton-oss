# [Alpha preview] Graviton CDK – "Infrastructure as Lego"

![Alt text](graviton.jpg)

![Build status](https://github.com/OrbitCloud/Graviton/actions/workflows/build.yml/badge.svg)
![License](https://img.shields.io/badge/License-MIT-green)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/charliermarsh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

## Overview

Graviton CDK is a modular infrastructure as code (IaC) development kit that enables composing secure, reliable and manageable infrastructure stacks using reusable components akin to building Lego.

> :warning: **WARNING**: This project is an alpha preview (v0.x.x) and under development. Breaking changes should be expected.

## Development

```ansi
Usage: make <command>

Initialize dev environment
    install              Install Poetry dependencies
    install-precommit    Install pre-commit hooks
    install-poly         Install polylith plugins
    install-lego         Install lego acme cli

Local development
    stacks               Check for changes in stacks
    test                 Run tests
    fmt                  Ruff formatter and linter (autofix)
    lint                 Ruff formatter and linter (check mode)
    pyright              Run Pyright type checker

Scaffolding
    component            Create a new component
    base                 Create a new base

Dependency choirs
    outdated             Check for outdated Poetry dependencies
    update               Update Poetry and pre-commit dependencies

Help
    help                 (Default) Print listing of key targets with their descriptions
```

## Adding components & bases

- Structure based on [Polylith](https://polylith.gitbook.io/polylith/) & [python-polylith](https://github.com/DavidVujic/python-polylith).

```bash
# Create a new component
poetry poly create component --name <component_name>

# Create a new base
poetry poly create base --name <base_name>

```

## Versioning & Commit messages

Releases are automatically created by commitizen in the build workflow when a
commit is pushed to the `main` branch. To communicate the intent of your changes
to the release process, please use the following prefixes:

- `feat:` New feature - will trigger a minor version bump
- `fix:` Bug fix - will trigger a patch version bump
- `test:` Adding or updating tests
- `refactor:` Code refactor
- `style:` Code style update
- `chore:` Maintenance task (e.g. bumping dependencies)
- `docs:` Documentation update
- `ci`: CI/CD related changes

### Breaking changes

When commitizen sees `BREAKING CHANGE` in the commit message, it will trigger a
major version bump – `cz commit` is your friend here and will automatically
include the breaking changes in the changelog and release message.

Right now we've set `major_version_zero = true` in `pyproject.toml` which means
that we're still in v0.x.x and breaking changes will not trigger a major version
as all versions are considered unstable.
