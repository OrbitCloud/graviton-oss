from pulumi_azure_native import app
from pydantic import AnyUrl, BaseModel, ConfigDict


class AppCorsConfig(BaseModel):
    allow_credentials: bool = False
    allowed_origins: list[AnyUrl]
    allowed_methods: list[str] | None = None
    allowed_headers: list[str] | None = None
    expose_headers: list[str] | None = None

    def cors_policy_args(self) -> app.CorsPolicyArgs:
        return app.CorsPolicyArgs(
            allowed_origins=[str(url).removesuffix("/") for url in self.allowed_origins],
            allowed_methods=self.allowed_methods,
            allowed_headers=self.allowed_headers,
            expose_headers=self.expose_headers,
            allow_credentials=self.allow_credentials,
        )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")
