from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RegistrationInputSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    output_dir: str | None = None
    out: str | None = None
    app_name: str | None = None
    app_version: str | None = None
    app_short_name: str | None = None
    app_type: str | None = None
    company: str | None = None
    contact_info: str | None = None
    spec_path: str | None = None
    source_text: str | None = None
    data: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_required(self) -> "RegistrationInputSchema":
        if not (self.output_dir or self.out):
            raise ValueError("Missing output_dir/out")
        if not (self.app_name or (self.data or {}).get("app__name")):
            raise ValueError("Missing app_name")
        return self

    def resolved_output_dir(self) -> str:
        return (self.output_dir or self.out or "").strip()


class RegistrationOutputSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    app__name: str = Field(min_length=1)
    app__short_name: str = ""
    app__version: str = Field(min_length=1)
    env__dev_lang: str = "待补充"
    env__dev_platform: str = "待补充"
    env__run_platform: str = "待补充"
    product__app_domain: str = "企业管理"

    holder__name: str = ""
    holder__address: str = ""
    holder__zip_code: str = ""
    holder__contact_name: str = ""
    holder__contact_mobile: str = ""
    holder__contact_email: str = ""
    holder__contact_landline: str = ""
    holder__tech_contact_name: str = ""
    holder__tech_contact_mobile: str = ""
