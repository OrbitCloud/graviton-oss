from hashlib import md5
from typing import Any, Dict, NotRequired, Optional, TypedDict

import pulumi
import yaml
from pulumi_command.local import Command, CommandArgs, run
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class PulumiEscEnvConfig(BaseModel):
    imports: Optional[list[str]] = Field(default=None, exclude=True)
    azure: Optional[Dict[str, Any]] = None
    pulumi_config: Optional[Dict[str, Any]] = None
    environment_variables: Optional[dict[str, str]] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    def write_yaml(self, env_name: str) -> tuple[str, str]:
        """Serialize the model to a yaml file and return the filename and checksum.

        Args:
            env_name (str): Name of the environment

        Returns:
            tuple[str, str]: Filename and checksum of the yaml file
        """
        data = {}
        data["values"] = self.model_dump(by_alias=True)
        if self.imports:
            data["imports"] = self.imports

        data_yaml: str = yaml.dump(data=data)

        filename: str = f"esc-{env_name}.yaml"
        checksum: str = md5(string=data_yaml.encode()).hexdigest()

        with open(file=filename, mode="w") as f:
            f.write(data_yaml)

        return filename, checksum


class PulumiEscEnvInputSchema(TypedDict):
    imports: NotRequired[Optional[list[str]]]
    azure: NotRequired[Optional[dict[str, Any]]]
    pulumi_config: NotRequired[Optional[dict[str, Any]]]
    environment_variables: NotRequired[Optional[dict[str, str]]]


class PulumiEscEnv(pulumi.ComponentResource):
    def __init__(
        self,
        env_name: str,
        input: PulumiEscEnvInputSchema,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__(
            "Graviton:PulumiEscEnv",
            name=f"esc-env-{env_name}",
            props=None,
            opts=opts,
        )

        self.env_name: str = env_name
        self.input: PulumiEscEnvInputSchema = input

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
                *PulumiEscEnvConfig.model_validate(obj=input).write_yaml(env_name=self.env_name)
            )
        )

    def _esc_env_update(self, filename: str, checksum: str) -> None:
        """Callback function to update the ESC configuration with the given yaml file.

        Args:
            filename (str): Temporary yaml file to update the ESC configuration with.
            checksum (str): Checksum of the yaml file used to trigger an update.
        """
        Command(
            resource_name=f"esc-env-{self.env_name}",
            args=CommandArgs(
                create=f"esc env init {pulumi.get_organization()}/{self.env_name} -f {filename}",
                update=f"esc env edit --editor tee {pulumi.get_organization()}/{self.env_name} < {filename} && echo {checksum} > /dev/null",
                delete=f"esc env rm -y {pulumi.get_organization()}/{self.env_name}",
            ),
            opts=pulumi.ResourceOptions.merge(
                opts1=self._opts, opts2=pulumi.ResourceOptions(delete_before_replace=True)
            ),
        ).id.apply(func=lambda _: run(command=f"rm {filename}"))
