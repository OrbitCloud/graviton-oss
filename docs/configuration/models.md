# Configuration

Graviton bases use a strict configuration schema to ensure that all required
configurations are set. Stacks are configured using [Pulumi stack YAML configuration
files](https://www.pulumi.com/docs/iac/concepts/config/).

## Strictly typed and validated configurations

Behind the scenes, Graviton uses [Pydantic](https://docs.pydantic.dev/latest/)
to validate configurations in a strictly typed manner. Additionally we might use
custom validation logic to ensure cloud resources are configured securely.

- **Security**: Ensure that cloud resources are configured correctly and in some
cases, to prevent accidental misconfigurations.
- **Consistency**: Ensure that all resources are configured in a consistent manner.
- **Ease of use**: Provide a clear and consistent way to configure resources.
Developers can get instant feedback on configuration errors with YAML language
servers which support schema validation.
- **Documentation**: Configuration schemas are self-documenting and provide
information on what configurations are required and optional.

## Example configuration model

The following is an example of a configuration model for Azure Container Apps
HTTP ingress:

```python
class HttpIngressConfig(BaseModel):
    protocol: Literal["http"]
    https_only: bool | None = True

    external: bool | None = False
    target_port: int

    custom_domains: list[CustomDomainConfig] | None = None
    ip_allow_list: list[PrivateIPv4Network | PublicIPv4Network | StrRef] | None = None

    cors: AppCorsConfig | None = None
    sticky_sessions: app.Affinity | None = app.Affinity.NONE
    client_certificate_mode: app.IngressClientCertificateMode = (
        app.IngressClientCertificateMode.IGNORE
    )
```
