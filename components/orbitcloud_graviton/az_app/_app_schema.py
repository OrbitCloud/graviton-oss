from pydantic import BaseModel, ConfigDict, Field


class ContainerResourcesConfig(BaseModel):
    cpu: float = Field(
        default=0.25,
        ge=0.1,
        le=4.0,
        description="The CPU request for the container. Default is 0.5. Minimum value is 0.5. Maximum value is 4.0.",
    )
    memory_gb: float = Field(
        default=0.5,
        ge=0.1,
        le=16.0,
        description="The memory request for the container. Default is 0.25Gi. Maximum is 8Gi for consumption and 16Gi for dedicated environments.",
    )

    CONSUMPTION_COMBINATIONS: list[tuple[float, float]] = [
        (0.25, 0.5),
        (0.5, 1.0),
        (0.75, 1.5),
        (1.0, 2.0),
        (1.25, 2.5),
        (1.5, 3.0),
        (1.75, 3.5),
        (2.0, 4.0),
        (2.25, 4.5),
        (2.5, 5.0),
        (2.75, 5.5),
        (3.0, 6.0),
        (3.25, 6.5),
        (3.5, 7),
        (3.75, 7.5),
        (4.0, 8),
    ]

    def validate_consumption_combinations(self) -> None:
        if (self.cpu, self.memory_gb) not in self.CONSUMPTION_COMBINATIONS:
            raise ValueError(
                f"Invalid combination of CPU and memory when using the consumption profile: {self.cpu} CPU and {self.memory_gb} memory. Valid combinations are: {self.CONSUMPTION_COMBINATIONS}"
            )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")
