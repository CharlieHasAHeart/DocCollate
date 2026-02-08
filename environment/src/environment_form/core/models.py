from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EnvironmentInputSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    output_dir: str | None = None
    out: str | None = None
    app_name: str | None = None
    app_version: str | None = None
    app_type: str | None = None
    spec_path: str | None = None
    source_text: str | None = None
    data: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_required(self) -> "EnvironmentInputSchema":
        if not (self.output_dir or self.out):
            raise ValueError("Missing output_dir/out")
        return self

    def resolved_output_dir(self) -> str:
        return (self.output_dir or self.out or "").strip()


class EnvironmentOutputSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    env__server_os: str = Field(min_length=1)
    env__server_soft: str = Field(min_length=1)
    env__server_model: str = Field(min_length=1)
    env__server_config: str = Field(min_length=1)
    env__server_id: str = Field(min_length=1)

    env__client_os: str = Field(min_length=1)
    env__client_soft: str = Field(min_length=1)
    env__client_model: str = Field(min_length=1)
    env__client_config: str = Field(min_length=1)
    env__client_id: str = Field(min_length=1)
