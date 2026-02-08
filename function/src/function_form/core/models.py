from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FunctionItem(BaseModel):
    name: str = Field(min_length=1)
    desc: str = Field(min_length=1)


class FunctionModule(BaseModel):
    name: str = Field(min_length=1)
    items: list[FunctionItem] = Field(min_length=1)


class SecondaryFunction(BaseModel):
    name: str = Field(min_length=1)
    desc: str = Field(min_length=1)


class PrimaryFunction(BaseModel):
    name: str = Field(min_length=1)
    secondary: list[SecondaryFunction] = Field(default_factory=list)


class LLMFunctionSchema(BaseModel):
    primary_functions: list[PrimaryFunction] = Field(min_length=1)


class FunctionInputSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    output_dir: str | None = None
    out: str | None = None
    app_name: str | None = None
    app_version: str | None = None
    app_short_name: str | None = None
    spec_path: str | None = None
    source_text: str | None = None
    data: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_required(self) -> "FunctionInputSchema":
        if not (self.output_dir or self.out):
            raise ValueError("Missing output_dir/out")
        if not (self.app_name or (self.data or {}).get("app__name")):
            raise ValueError("Missing app_name")
        return self

    def resolved_output_dir(self) -> str:
        return (self.output_dir or self.out or "").strip()


class FunctionOutputSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    app__name: str = Field(min_length=1)
    app__version: str = Field(min_length=1)
    module_list: list[FunctionModule] = Field(min_length=1)
