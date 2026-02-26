# Graviton CDK -- Infrastructure as Lego

![Alt text](graviton.jpg)

![Build status](https://github.com/OrbitCloud/Graviton/actions/workflows/build.yml/badge.svg)
![License](https://img.shields.io/badge/License-MIT-green)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/charliermarsh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

## Overview

Graviton CDK is a Python infrastructure-as-code library for Azure, built on
[Pulumi](https://www.pulumi.com/). It provides a collection of opinionated,
composable building blocks -- **components** and **bases** -- that snap together
like Lego to form complete cloud environments.

Instead of writing hundreds of lines of resource definitions, platform
engineering teams compose pre-built components (networking, compute, storage,
IAM, monitoring, and more) into higher-level bases (landing zones, hub-spoke
networks, workload identities) that encode best practices out of the box.

## Features

- **25+ Azure components** -- networking, compute, storage, container registry,
  Key Vault, Event Hub, Service Bus, PostgreSQL, SQL, AI services, monitoring,
  and more.
- **14 composable bases** -- landing zones, hub-spoke networking, workload
  identities, app workloads, firewall, Oracle DB, ACME SSL, and others.
- **Pydantic-powered configuration** -- every resource is configured through
  validated Pydantic models with sensible defaults.
- **Built on Pulumi** -- full Python expressiveness, real programming constructs,
  and access to the entire Pulumi ecosystem.
- **Polylith architecture** -- components and bases are independently
  developable, testable, and reusable.

## Quick Start

Deploy a landing zone with a single function call. Graviton reads its
configuration from your Pulumi stack config:

```python
from orbitcloud_graviton.landing_zone import deploy_landing_zone

deploy_landing_zone()
```

The landing zone is driven by your `Pulumi.<stack>.yaml` configuration:

```yaml
config:
  # The namespace (before the colon) is your Pulumi project name
  landing_zone:has_keyvault: true
  landing_zone:has_container_registry: true
```

Run `pulumi up` and your entire environment is provisioned.

## Installation

```bash
pip install orbitcloud-graviton
```

Or with Poetry:

```bash
poetry add orbitcloud-graviton
```

## Project Structure

Graviton follows the [Polylith](https://polylith.gitbook.io/polylith/)
architecture. **Components** (`components/`) wrap individual Azure services with
opinionated defaults. **Bases** (`bases/`) compose components into higher-level
deployment patterns.

## Versioning

Graviton follows [semver](https://semver.org/). See the
[releases](https://github.com/OrbitCloud/graviton-oss/releases) page for the
latest version and changelog.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for
development setup, coding conventions, and commit message guidelines.

## License

MIT -- see the [LICENSE](LICENSE) file for details.
