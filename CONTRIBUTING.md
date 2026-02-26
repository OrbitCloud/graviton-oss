# Contributing to Graviton CDK

Thanks for your interest in contributing to Graviton CDK! This document covers
the development workflow, project conventions, and how to add new components.

## Development

The project uses a Makefile for common tasks:

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

Dependency chores
    outdated             Check for outdated Poetry dependencies
    update               Update Poetry and pre-commit dependencies

Help
    help                 (Default) Print listing of key targets with their descriptions
```

## Adding Components & Bases

The project structure is based on
[Polylith](https://polylith.gitbook.io/polylith/) and
[python-polylith](https://github.com/DavidVujic/python-polylith).

```bash
# Create a new component
poetry poly create component --name <component_name>

# Create a new base
poetry poly create base --name <base_name>
```

**Components** (`components/`) wrap individual Azure services with opinionated
defaults and Pydantic configuration models.

**Bases** (`bases/`) compose multiple components into higher-level deployment
patterns (e.g., a landing zone that provisions networking, Key Vault, and
monitoring together).

## Versioning & Commit Messages

Releases are automatically created by
[commitizen](https://commitizen-tools.github.io/commitizen/) in the build
workflow when a commit is pushed to the `main` branch. Use the following prefixes
to communicate intent:

| Prefix       | Purpose                               | Version impact |
|--------------|---------------------------------------|----------------|
| `feat:`      | New feature                           | Minor bump     |
| `fix:`       | Bug fix                               | Patch bump     |
| `test:`      | Adding or updating tests              | --             |
| `refactor:`  | Code refactor                         | --             |
| `style:`     | Code style update                     | --             |
| `chore:`     | Maintenance (e.g. bumping deps)       | --             |
| `docs:`      | Documentation update                  | --             |
| `ci:`        | CI/CD related changes                 | --             |

### Breaking Changes

When commitizen sees `BREAKING CHANGE` in the commit message body, it triggers a
major version bump. Use `cz commit` to interactively build a commit message that
includes breaking change notes -- these are automatically included in the
changelog and release notes.

> **Note**: The project currently has `major_version_zero = true` in
> `pyproject.toml`, meaning breaking changes bump the minor version rather than
> the major version while the project is in v0.x.x.
