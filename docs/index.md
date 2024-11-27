# Graviton

## Production ready infrastructure modules for Azure

Graviton CDK is designed to simplify the process of creating and managing cloud
infrastructure. It provides a set of reusable components that can be combined to
build complex infrastructure stacks.

!!! warning
    The project is currently in alpha stage (v0.x.x), so it is still
    under active development and may undergo significant changes. Users should be
    prepared for potential breaking changes as the project evolves.

    This documentation is a work in progress and may not be complete.

    We expect users to have a general understanding of cloud infrastructure concept
    and be aware that resources created by Graviton will incur costs in your
    Azure subscription.

## Crafted with :heart: by Orbit

Graviton is an open-source project developed and used by [Orbit](https://orbit.is).
We are a team of cloud experts with years of experience running production workloads
in the enterprise and startup space. We provide consulting services and develop
tools to help organizations adopt cloud technologies and modern software development
practices.

Interested in working with us? [Get in touch](https://orbit.is/contact)!

## Summary

- [x] Primarily focused on infrastructure for application workloads on Azure.
- [x] Ready to use templated infrastructure stacks for wide range of workloads.
- [x] Built on top of [Pulumi IaC (Infrastructure as Code) framework](https://www.pulumi.com/)
with Python as the primary language.
- [x] Based on reusable and composable components with sane and secure defaults from
operational best practices and years of experience running production workloads
in Azure.

## Before you begin

Although Graviton is designed to be easy to use, there are a few pre-requisites
that you should be aware of before you start using it:

## General prerequisites

- You should have a general understanding of cloud infrastructure concept and be
aware that resources created by Graviton will incur costs in your Azure subscription.
- Have a general understanding of using [Pulumi](https://www.pulumi.com/). Head
over to the [Pulumi documentation](https://www.pulumi.com/docs/) to get started.

### Software requirements

- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
installed and authenticated.
- [Python 3.12+](https://www.python.org/downloads/) installed.
- [Pulumi CLI](https://www.pulumi.com/docs/iac/download-install/) installed.
