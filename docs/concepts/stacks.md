# Stacks

Graviton uses Pulumi for provisioning resources. Pulumi uses stacks to configure,
group and manage resources in the cloud. Stacks are a way to manage resources as
a single unit. Stacks generally consist of services and resources that are related
to each other.

!!! info
    For information on stacks in Pulumi, refer to the
    [Pulumi documentation](https://www.pulumi.com/docs/iac/concepts/stacks/).

## Configuring stacks in Graviton

Templated stacks in Graviton are called
[bases](https://github.com/OrbitCloud/graviton-oss/tree/main/bases). Bases consist
of a set of reusable
[components](https://github.com/OrbitCloud/graviton-oss/tree/main/bases)
(usually Azure services).

You may need to set different configurations depending on the configuration schema
defined by a base.

### Example stack configuration

Pulumi stack configuration files are written in YAML. The following is an example
of a stack configuration file for a Graviton stack:

```yaml title="Pulumi.prod.yaml"
config:
  azure-native:location: northeurope
  azure-native:subscriptionId: 00000000-0000-0000-0000-000000000000
  azure-native:tenantId: 00000000-0000-0000-0000-000000000000
  azuread:tenantId: 00000000-0000-0000-0000-000000000000
  env: prod
  workload_name: myapp
```

### Required configurations

- `env`: The environment in which the stack is deployed (e.g. `dev`, `staging`, `prod`).
- `workload_name`: The name of the workload that the stack is deploying.
- `azure-native:location`: The Azure region where the resources will be deployed.
- `azure-native:tenantId`: The Azure tenant ID.
- `azure-native:subscriptionId`: The Azure subscription ID.
- `azuread:tenantId`: Entra tenant ID.

!!! info
    Although setting the `tenantId` and `subscriptionId` is not strictly required
    by the Pulumi Azure & Entra providers, we require them to ensure resources
    are created in the correct Azure subscription and tenant.

### Optional configurations

- `resource_group_name`: The name of the resource group where the resources will
be deployed. If not provided, a new resource group will be created.
