from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class AssessmentInputSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    output_dir: str | None = None
    out: str | None = None
    app_name: str | None = None
    app_version: str | None = None
    assess_dev_date: str | None = None
    assess_completion_date: str | None = None
    assess_workload: str | None = None
    spec_path: str | None = None
    source_text: str | None = None
    data: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_required(self) -> "AssessmentInputSchema":
        if not (self.output_dir or self.out):
            raise ValueError("Missing output_dir/out")
        if not (self.assess_dev_date or "").strip():
            raise ValueError("Missing assess_dev_date")
        if not (self.assess_completion_date or "").strip():
            raise ValueError("Missing assess_completion_date")
        if not (self.assess_workload or "").strip():
            raise ValueError("Missing assess_workload")
        return self

    def resolved_output_dir(self) -> str:
        return (self.output_dir or self.out or "").strip()


class AssessmentOutputSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    product__service_object: str = ""
    product__main_functions: str = ""
    product__tech_specs: str = ""
    app__product_type_text: str = "应用软件-信息管理软件"
    env__memory_req: str = "512MB"
    env__hardware_model: str = "通用计算机"
    env__os: str = "Windows 10/11、Linux"
    env__language: str = "Python"
    env__database: str = "PostgreSQL 13"
    env__soft_scale: str = "中"
    env__os_version: str = "Ubuntu 22.04 LTS"
    env__hw_dev_platform: str = "CPU：4核；内存：8GB；存储：256GB SSD"
    env__sw_dev_platform: str = "Windows 10/11、VS Code、Python 3.10+"
    assess__workload: str = "3人*3月"
    app__category_assess: str = "30 其他计算机应用软件和信息服务"
    assess__dev_date: str = ""
    assess__completion_date: str = ""

    assess__support_floppy: bool = False
    assess__support_sound: bool = False
    assess__support_cdrom: bool = False
    assess__support_gpu: bool = False
    assess__support_other: bool = False
    assess__is_self_dev: bool = True
    assess__has_docs: bool = True
    assess__has_source: bool = True

    assess__product_mode_val: str = "pure"
    assess__is_embedded: bool = False
