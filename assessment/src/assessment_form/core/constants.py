from __future__ import annotations

CHECKED_SYMBOL = "☑"
UNCHECKED_SYMBOL = "☐"

CELL_MAP_TEXT = {
    "product__service_object": (0, "B2"),
    "product__main_functions": (0, "B3"),
    "product__tech_specs": (0, "B4"),
    "app__product_type_text": (0, "B5"),
    "env__memory_req": (1, "B3"),
    "env__hardware_model": (1, "E3"),
    "env__os": (1, "B8"),
    "env__language": (1, "E8"),
    "env__database": (1, "B9"),
    "env__soft_scale": (1, "E9"),
    "env__os_version": (1, "B10"),
    "env__hw_dev_platform": (1, "C12"),
    "env__sw_dev_platform": (1, "C14"),
    "assess__workload": (2, "C7"),
    "app__category_assess": (2, "B10"),
    "assess__dev_date": (2, "C5"),
    "assess__completion_date": (2, "C6"),
}

CELL_MAP_CHECKBOX = {
    "assess__support_floppy": (1, "A4"),
    "assess__support_sound": (1, "D4"),
    "assess__support_cdrom": (1, "A5"),
    "assess__support_gpu": (1, "D5"),
    "assess__support_other": (1, "A6"),
    "assess__is_self_dev": (2, "A2"),
    "assess__has_docs": (2, "A3"),
    "assess__has_source": (2, "A4"),
}

CELL_MODE_PURE = (2, "C8")
CELL_MODE_EMBEDDED = (2, "C9")

WRAP_TEXT_KEYS = {
    "product__service_object",
    "product__main_functions",
    "product__tech_specs",
    "app__product_type_text",
    "env__os",
    "env__hw_dev_platform",
    "env__sw_dev_platform",
    "app__category_assess",
}
