from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApplicantInfoSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    phone: str | None = None
    address: str | None = None
    zip_code: str | None = None
    contact_person: str | None = None
    mobile: str | None = None
    email: str | None = None
    fax: str | None = None


class CopyrightHolderSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    category: str | None = None
    id_type: str | None = None
    id_number: str | None = None
    nationality: str | None = None
    city: str | None = None
    found_date: str | None = None


class CompanyProfileSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    applicant_info: ApplicantInfoSchema | dict[str, Any] | None = None
    copyright_holders: list[CopyrightHolderSchema] | None = None


class CopyrightInputSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    out: str | None = None
    output_dir: str | None = None
    app_name: str | None = None
    app_version: str | None = None
    completion_date: str | None = None
    company: str | None = None
    source_text: str | None = None
    spec_path: str | None = None
    company_profile: CompanyProfileSchema | dict[str, Any] | None = None
    data: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_required_fields(self) -> "CopyrightInputSchema":
        out_value = (self.out or self.output_dir or "").strip()
        if not out_value:
            raise ValueError("Missing output directory in JSON: out or output_dir")
        if not (self.completion_date or "").strip():
            raise ValueError("Missing completion_date in input JSON")

        has_data = isinstance(self.data, dict) and bool(self.data)
        has_source = bool((self.source_text or "").strip()) or bool((self.spec_path or "").strip())
        if not has_data and not has_source:
            raise ValueError("Provide either data, source_text, or spec_path in input JSON")
        return self

    def resolved_output_dir(self) -> str:
        return (self.out or self.output_dir or "").strip()


class RightsSuccessionDetailsSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    is_registered: bool = False
    original_id: str = ""
    is_modified: bool = False
    modified_cert_id: str = ""


class RightsPartialRightsSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    publish: bool = False
    attribution: bool = False
    modification: bool = False
    copy: bool = False
    distribution: bool = False
    rental: bool = False
    network: bool = False
    translation: bool = False
    other: bool = False


class ModificationDetailsSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    authorized: bool = False
    registered: bool = False
    original_id: str = ""
    description: str = ""


class CopyrightOutputSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    # core/raw fields used by pipeline + renderer
    app__name: str = Field(min_length=1)
    app__version: str = Field(default="未标注版本", min_length=1)
    app__short_name: str | None = None
    app__classification_code: str = ""

    applicant__type: str = "holder"

    copyright__completion_date: str = ""
    copyright__development_method: str = "独立开发"
    copyright__status_published: bool = False
    copyright__publish_date: str = ""
    copyright__publish_location: str = ""

    rights__acquire_method: str = "原始取得"
    rights__scope: str = "全部"
    rights__succession_details: RightsSuccessionDetailsSchema = Field(
        default_factory=RightsSuccessionDetailsSchema
    )
    rights__partial_rights: RightsPartialRightsSchema = Field(default_factory=RightsPartialRightsSchema)

    modification_details: ModificationDetailsSchema | None = None
    signature__date: str = ""

    tech__source_lines: str = ""
    tech__hardware_dev: str = ""
    tech__hardware_run: str = ""
    tech__os_dev: str = ""
    tech__os_run: str = ""
    tech__dev_tools: str = ""
    tech__run_support: str = ""
    tech__language: str = ""
    tech__dev_purpose: str = ""
    tech__main_functions: str = ""
    tech__features: str = ""

    # template placeholders (scanned from DOCX)
    applicant__type_holder: str = ""
    applicant__type_agent: str = ""

    author_1__name: str = ""
    author_1__category: str = ""
    author_1__id_type: str = ""
    author_1__id_number: str = ""
    author_1__nationality: str = ""
    author_1__city: str = ""
    author_1__found_date: str = ""

    author_2__name: str = ""
    author_2__category: str = ""
    author_2__id_type: str = ""
    author_2__id_number: str = ""
    author_2__nationality: str = ""
    author_2__city: str = ""
    author_2__found_date: str = ""

    author_3__name: str = ""
    author_3__category: str = ""
    author_3__id_type: str = ""
    author_3__id_number: str = ""
    author_3__nationality: str = ""
    author_3__city: str = ""
    author_3__found_date: str = ""

    applicant__name: str = ""
    applicant__phone: str = ""
    applicant__address: str = ""
    applicant__zip_code: str = ""
    applicant__contact_person: str = ""
    applicant__mobile: str = ""
    applicant__email: str = ""
    applicant__fax: str = ""

    agent__name: str = ""
    agent__phone: str = ""
    agent__address: str = ""
    agent__zip_code: str = ""
    agent__contact_person: str = ""
    agent__mobile: str = ""
    agent__email: str = ""
    agent__fax: str = ""

    copyright__completion_year: str = ""
    copyright__completion_month: str = ""
    copyright__completion_day: str = ""

    copyright__dev_method_independent: str = ""
    copyright__dev_method_cooperative: str = ""
    copyright__dev_method_commissioned: str = ""
    copyright__dev_method_task_assigned: str = ""

    rights__acquire_original: str = ""
    rights__acquire_succession: str = ""
    rights__succession_assignment: str = ""
    rights__succession_assumption: str = ""
    rights__succession_inherit: str = ""
    rights__succession_is_registered: str = ""
    rights__succession_original_id: str = ""
    rights__succession_is_modified: str = ""
    rights__succession_modified_cert_id: str = ""

    rights__scope_all: str = ""
    rights__scope_partial: str = ""
    rights__partial_publish: str = ""
    rights__partial_attribution: str = ""
    rights__partial_modification: str = ""
    rights__partial_copy: str = ""
    rights__partial_distribution: str = ""
    rights__partial_rental: str = ""
    rights__partial_network: str = ""
    rights__partial_translation: str = ""
    rights__partial_other: str = ""

    copyright__app_type_original: str = ""
    copyright__app_type_modified: str = ""
    copyright__app_modified_auth: str = ""
    copyright__app_modified_registered: str = ""
    copyright__app_modified_original_id: str = ""
    copyright__app_modified_description: str = ""

    signature__year: str = ""
    signature__month: str = ""
    signature__day: str = ""

    @model_validator(mode="after")
    def normalize_short_name(self) -> "CopyrightOutputSchema":
        if not self.app__short_name:
            self.app__short_name = self.app__name
        return self
