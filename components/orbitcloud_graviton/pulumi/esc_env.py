from hashlib import md5
from typing import Any, Dict, Optional

import pulumi
import yaml
from pulumi_command.local import Command, CommandArgs, run
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class PulumiEnvConfigValues(BaseModel):
    azure: Optional[Dict[str, Any]] = None
    pulumi_config: Optional[Dict[str, Any]] = None
    environment_variables: Optional[dict[str, str]] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="allow",
    )


class PulumiEnvConfig(BaseModel):
    env_name: str
    imports: Optional[list[str]] = None
    values: PulumiEnvConfigValues = PulumiEnvConfigValues()

    model_config = ConfigDict(extra="forbid")

    def write_yaml(self) -> tuple[str, str]:
        """Serialize the model to a yaml file and return the filename and checksum.

        Returns:
            tuple[str, str]: Filename and checksum of the yaml file
        """

        data: str = yaml.dump(self.model_dump(by_alias=True, exclude_none=True))

        filename: str = f"esc-{self.env_name}.yaml"
        checksum: str = md5(string=data.encode()).hexdigest()

        with open(file=filename, mode="w") as f:
            f.write(data)

        pulumi.info(msg=f"ESC environment: {self.env_name}")
        pulumi.info(msg=data)

        return filename, checksum


class PulumiEnv(pulumi.ComponentResource):
    def __init__(
        self,
        config: PulumiEnvConfig,
        input: dict,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__(
            "Graviton:PulumiEscEnv",
            name=f"esc-env-{config.env_name}",
            props=None,
            opts=opts,
        )

        self.config: PulumiEnvConfig = config
        self.input = input
        self._opts: pulumi.ResourceOptions = pulumi.ResourceOptions.merge(
            opts1=opts, opts2=pulumi.ResourceOptions(parent=self)
        )

        self._esc_env()

    def _esc_env(self) -> None:
        """Update the ESC configuration with the given input

        The model is validated and serialized to a yaml file which is passed to _esc_env_update()
        along with its checksum which changes trigger update.
        """

        pulumi.Output.from_input(val=self.input).apply(
            func=lambda input: self._esc_env_update(
                *PulumiEnvConfig.model_validate(obj=input).write_yaml()
            )
        )

    def _esc_env_update(self, filename: str, checksum: str) -> None:
        """Callback function to update the ESC configuration with the given yaml file.

        Args:
            filename (str): Temporary yaml file to update the ESC configuration with.
            checksum (str): Checksum of the yaml file used to trigger an update.
        """
        Command(
            resource_name=f"esc-env-{self.config.env_name}",
            args=CommandArgs(
                create=f"esc env init {pulumi.get_organization()}/{self.config.env_name} -f {filename}",
                update=f"esc env edit --editor tee {pulumi.get_organization()}/{self.config.env_name} < {filename} && echo {checksum} > /dev/null",
                delete=f"esc env rm -y {pulumi.get_organization()}/{self.config.env_name}",
            ),
            opts=pulumi.ResourceOptions.merge(
                opts1=self._opts, opts2=pulumi.ResourceOptions(delete_before_replace=True)
            ),
        ).id.apply(func=lambda _: run(command=f"rm {filename}"))
