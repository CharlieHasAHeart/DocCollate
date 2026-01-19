from __future__ import annotations

from .constants import CELL_MAP_CHECKBOX, CELL_MAP_TEXT

TEST_FORMS_DIRECT_FIELDS = {
    "app__category_assess",
    "app__name",
    "app__product_type_text",
    "app__short_name",
    "app__version",
    "assess__completion_date",
    "assess__dev_date",
    "assess__has_docs",
    "assess__has_source",
    "assess__is_embedded",
    "assess__is_self_dev",
    "assess__product_mode_val",
    "assess__support_cdrom",
    "assess__support_floppy",
    "assess__support_gpu",
    "assess__support_other",
    "assess__support_sound",
    "assess__workload",
    "env__client_model",
    "env__database",
    "env__dev_lang",
    "env__dev_platform",
    "env__hardware_model",
    "env__hw_dev_platform",
    "env__language",
    "env__memory_req",
    "env__os",
    "env__os_version",
    "env__run_platform",
    "env__server_model",
    "env__soft_scale",
    "env__sw_dev_platform",
    "product__app_domain",
    "product__func_list",
    "product__main_functions",
    "product__service_object",
    "product__tech_specs",
}

TEST_FORMS_DIRECT_FIELDS.update(CELL_MAP_TEXT.keys())
TEST_FORMS_DIRECT_FIELDS.update(CELL_MAP_CHECKBOX.keys())

COPYRIGHT_DIRECT_FIELDS = {
    "app__classification_code",
    "app__name",
    "app__short_name",
    "app__version",
    "applicant__type",
    "copyright__completion_date",
    "copyright__development_method",
    "copyright__publish_date",
    "copyright__publish_location",
    "copyright__status_published",
    "modification_details",
    "rights__acquire_method",
    "rights__partial_rights",
    "rights__scope",
    "rights__succession_details",
    "signature__date",
    "tech__dev_purpose",
    "tech__dev_tools",
    "tech__features",
    "tech__hardware_dev",
    "tech__hardware_run",
    "tech__language",
    "tech__main_functions",
    "tech__os_dev",
    "tech__os_run",
    "tech__run_support",
    "tech__source_lines",
}

DIRECT_FIELDS_BY_TARGET = {
    "proposal": set(),
    "test_forms": TEST_FORMS_DIRECT_FIELDS,
    "copyright": COPYRIGHT_DIRECT_FIELDS,
}

FIELD_DEPENDENCIES = {
    "app__product_type_text": {"app__product_type"},
    "env__dev_lang": {"env__language"},
    "env__dev_platform": {"env__sw_dev_platform"},
    "env__run_platform": {"env__os"},
    "product__main_functions": {"product__func_list"},
    "tech__dev_purpose": {"product__service_object"},
    "tech__dev_tools": {"env__sw_dev_platform"},
    "tech__features": {"product__tech_specs"},
    "tech__hardware_dev": {"env__hw_dev_platform"},
    "tech__language": {"env__language"},
    "tech__main_functions": {"product__main_functions"},
    "tech__os_dev": {"env__os_version", "env__os"},
    "tech__os_run": {"env__run_platform", "env__os"},
}


def expand_dependencies(fields: set[str]) -> set[str]:
    expanded = set(fields)
    changed = True
    while changed:
        changed = False
        for field in list(expanded):
            deps = FIELD_DEPENDENCIES.get(field, set())
            for dep in deps:
                if dep not in expanded:
                    expanded.add(dep)
                    changed = True
    return expanded


def required_fields_for_target(target: str) -> set[str]:
    direct = DIRECT_FIELDS_BY_TARGET.get(target, set())
    return expand_dependencies(set(direct))


def dependency_fields_for_target(target: str) -> set[str]:
    direct = DIRECT_FIELDS_BY_TARGET.get(target, set())
    required = expand_dependencies(set(direct))
    return required - set(direct)
