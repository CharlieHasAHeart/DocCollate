from __future__ import annotations

import random
import re

from ..core.constants import (
    CATEGORY_ID_OPTIONS,
    CLIENT_MODEL_POOL,
    CLIENT_OS_POOL,
    CLIENT_CONFIG_POOL,
    CLIENT_SOFT_POOL,
    PRODUCT_TYPE_CN,
    PRODUCT_TYPE_PREFIX,
    SERVER_MODEL_POOL,
    SERVER_OS_POOL,
    SERVER_CONFIG_POOL,
    SERVER_SOFT_POOL,
)
from ..core.date_utils import normalize_date_str
from ..config import DatesConfig


def sanitize_html_breaks(value: object) -> object:
    if isinstance(value, str):
        return (
            value.replace("<br />", "\n")
            .replace("<br/>", "\n")
            .replace("<br>", "\n")
        )
    if isinstance(value, list):
        return [sanitize_html_breaks(item) for item in value]
    if isinstance(value, dict):
        return {k: sanitize_html_breaks(v) for k, v in value.items()}
    return value


def sanitize_data(data: dict) -> dict:
    data = sanitize_html_breaks(data)
    data = normalize_list_fields(data)
    data = normalize_server_client_fields(data)
    return data


def normalize_list_fields(data: dict) -> dict:
    for key, value in list(data.items()):
        if isinstance(value, list):
            if key == "product__func_list":
                continue
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            data[key] = "\n".join(cleaned)
    return data


def normalize_server_client_fields(data: dict) -> dict:
    def split_server_client(text: str) -> tuple[str, str] | None:
        server_match = re.search(
            r"(服务器端|服务端|服务器)\s*[:：]?\s*(.+?)(?=(客户端|客户端软件|客户端环境)|$)",
            text,
        )
        client_match = re.search(r"(客户端|客户端软件|客户端环境)\s*[:：]?\s*(.+)$", text)
        if not server_match or not client_match:
            return None
        server_part = server_match.group(2).strip().strip("；;，,")
        client_part = client_match.group(2).strip().strip("；;，,")
        if not server_part or not client_part:
            return None
        return server_part, client_part

    pairs = [
        ("env__server_os", "env__client_os"),
        ("env__server_soft", "env__client_soft"),
        ("env__server_config", "env__client_config"),
        ("env__server_model", "env__client_model"),
    ]
    for server_key, client_key in pairs:
        combined = data.get(server_key, "")
        if isinstance(combined, str) and combined:
            split = split_server_client(combined)
            if split:
                data[server_key], data[client_key] = split
        combined = data.get(client_key, "")
        if isinstance(combined, str) and combined:
            split = split_server_client(combined)
            if split:
                data[server_key], data[client_key] = split
    return data


def pick_random_models() -> tuple[dict, dict]:
    server_choice = random.choice(SERVER_MODEL_POOL)
    client_choice = random.choice(CLIENT_MODEL_POOL)
    return server_choice, client_choice


def pick_random_os() -> tuple[str, str]:
    server_os = random.choice(SERVER_OS_POOL)
    client_os = random.choice(CLIENT_OS_POOL)
    return server_os, client_os


def pick_random_soft() -> tuple[str, str]:
    server_soft = random.choice(SERVER_SOFT_POOL)
    client_soft = random.choice(CLIENT_SOFT_POOL)
    return server_soft, client_soft


def pick_random_config() -> tuple[str, str]:
    server_config = random.choice(SERVER_CONFIG_POOL)
    client_config = random.choice(CLIENT_CONFIG_POOL)
    return server_config, client_config


def build_env_pool_data() -> dict[str, str]:
    server_os, client_os = pick_random_os()
    server_soft, client_soft = pick_random_soft()
    server_config, client_config = pick_random_config()
    return {
        "env__server_os": server_os,
        "env__client_os": client_os,
        "env__server_soft": server_soft,
        "env__client_soft": client_soft,
        "env__server_config": server_config,
        "env__client_config": client_config,
    }


def merge_missing(base: dict, updates: dict) -> dict:
    merged = dict(base)
    for key, value in updates.items():
        if key not in merged or merged[key] in (None, ""):
            merged[key] = value
    return merged


def normalize_product_type(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return "应用软件-信息管理软件"
    if "Other" in cleaned or "其他" in cleaned:
        return "应用软件-信息管理软件"
    for eng, cn in PRODUCT_TYPE_CN.items():
        if cn in cleaned or eng in cleaned:
            prefix = PRODUCT_TYPE_PREFIX.get(eng, "应用软件-")
            return f"{prefix}{cn}"
    return "应用软件-信息管理软件"


def normalize_category_id(value: str) -> str:
    value = value.strip()
    if not value:
        return value
    if value in CATEGORY_ID_OPTIONS:
        return value
    for opt in CATEGORY_ID_OPTIONS:
        if value in opt:
            return opt
    return value


def normalize_assessment_data(
    data: dict,
    dates_config: DatesConfig | None = None,
    required_fields: set[str] | None = None,
) -> dict:
    if not data:
        return data
    def is_required(field: str) -> bool:
        return required_fields is None or field in required_fields

    defaults = {
        "assess__support_floppy": False,
        "assess__support_sound": False,
        "assess__support_cdrom": False,
        "assess__support_gpu": False,
        "assess__support_other": False,
        "assess__is_self_dev": True,
        "assess__has_docs": True,
        "assess__has_source": True,
    }
    for key, value in defaults.items():
        if not is_required(key):
            continue
        if key not in data:
            data[key] = value
        elif isinstance(data[key], str):
            data[key] = data[key].strip().lower() in {"true", "yes", "1", "y", "是"}

    if is_required("assess__workload"):
        workload = str(data.get("assess__workload", "")).strip()
        if workload:
            numbers = re.findall(r"\d+", workload)
            people = int(numbers[0]) if numbers else 3
            months = int(numbers[1]) if len(numbers) > 1 else 3
            people = max(1, min(people, 6))
            months = max(1, months)
            data["assess__workload"] = f"{people}人*{months}月"
        else:
            data["assess__workload"] = "3人*3月"

    if is_required("env__memory_req"):
        memory = str(data.get("env__memory_req", "")).strip()
        if memory:
            digits = "".join(ch for ch in memory if ch.isdigit())
            if digits:
                data["env__memory_req"] = f"{digits}MB"

    if is_required("app__product_type_text"):
        app_type = str(data.get("app__product_type_text", "") or data.get("app__product_type", "")).strip()
        data["app__product_type_text"] = normalize_product_type(app_type)

    if is_required("app__category_assess"):
        category_id = str(data.get("app__category_assess", "")).strip()
        if category_id:
            data["app__category_assess"] = normalize_category_id(category_id)

    if is_required("env__soft_scale"):
        if data.get("env__soft_scale") not in {"大", "中", "小"}:
            data["env__soft_scale"] = "中"

    if is_required("env__database"):
        if not str(data.get("env__database", "")).strip():
            data["env__database"] = "PostgreSQL 13"
    if is_required("env__os_version"):
        if not str(data.get("env__os_version", "")).strip():
            data["env__os_version"] = "Ubuntu 22.04 LTS"

    if is_required("assess__product_mode_val"):
        if not data.get("assess__product_mode_val"):
            data["assess__product_mode_val"] = "pure"
    mode_value = str(data.get("assess__product_mode_val", "pure")).lower()
    if is_required("assess__is_pure") and "assess__is_pure" not in data:
        data["assess__is_pure"] = mode_value != "embedded"
    if is_required("assess__is_embedded") and "assess__is_embedded" not in data:
        data["assess__is_embedded"] = mode_value == "embedded"

    if is_required("copyright__completion_date") and data.get("copyright__completion_date"):
        data["copyright__completion_date"] = normalize_date_str(str(data.get("copyright__completion_date", "")))
    if is_required("assess__completion_date") and data.get("assess__completion_date"):
        data["assess__completion_date"] = normalize_date_str(str(data.get("assess__completion_date", "")))
    if is_required("assess__dev_date") and data.get("assess__dev_date"):
        data["assess__dev_date"] = normalize_date_str(str(data.get("assess__dev_date", "")))

    server_choice, client_choice = pick_random_models()
    if is_required("env__server_model") and not data.get("env__server_model"):
        data["env__server_model"] = server_choice["model"]
    if is_required("env__client_model") and not data.get("env__client_model"):
        data["env__client_model"] = client_choice["model"]

    # Always pick a single OS (with version) from pools for server/client.
    return data


def derive_fields(data: dict, required_fields: set[str] | None = None) -> dict:
    if not data:
        return data
    def is_required(field: str) -> bool:
        return required_fields is None or field in required_fields

    if is_required("app__classification_code"):
        data["app__classification_code"] = ""
    if is_required("tech__source_lines") and not data.get("tech__source_lines"):
        data["tech__source_lines"] = "15000"
    if is_required("app__short_name"):
        data["app__short_name"] = "无"

    func_list = data.get("product__func_list", [])
    need_func_list = is_required("product__func_list") or is_required("product__main_functions") or is_required("tech__main_functions")
    if need_func_list and isinstance(func_list, list) and func_list:
        for item in func_list:
            if not isinstance(item, dict):
                continue
            title = item.get("name") or item.get("一级功能") or ""
            desc = item.get("desc") or item.get("功能描述")
            if title and "name" not in item:
                item["name"] = title
            if title and "一级功能" not in item:
                item["一级功能"] = title
            if not desc and title:
                short = title[:6]
                desc = f"可以{short}管理。"
            if desc:
                item["desc"] = desc
                item["功能描述"] = desc

    if is_required("product__main_functions"):
        if not data.get("product__main_functions") and isinstance(func_list, list) and func_list:
            names = []
            for item in func_list:
                if isinstance(item, dict):
                    name = item.get("一级功能") or item.get("name")
                    if name:
                        names.append(name)
            if names:
                data["product__main_functions"] = "、".join(names[:5]) + "等功能"

    if is_required("tech__hardware_dev") and not data.get("tech__hardware_dev"):
        hw_dev = data.get("env__hw_dev_platform", "")
        if hw_dev:
            data["tech__hardware_dev"] = f"开发硬件环境：{hw_dev}"

    if is_required("tech__os_dev") and not data.get("tech__os_dev"):
        data["tech__os_dev"] = data.get("env__os_version", "") or data.get("env__os", "")

    if is_required("tech__os_run") and not data.get("tech__os_run"):
        run_platform = data.get("env__run_platform", "") or data.get("env__os", "")
        if run_platform:
            data["tech__os_run"] = run_platform

    if is_required("tech__dev_tools") and not data.get("tech__dev_tools"):
        dev_tools = data.get("env__sw_dev_platform", "")
        if dev_tools:
            data["tech__dev_tools"] = f"开发工具与平台：{dev_tools}"

    if is_required("tech__language") and not data.get("tech__language"):
        data["tech__language"] = data.get("env__language", "")

    if is_required("tech__dev_purpose") and not data.get("tech__dev_purpose"):
        service_object = data.get("product__service_object", "")
        if service_object:
            data["tech__dev_purpose"] = f"开发目的在于服务{service_object}，解决其业务需求。"

    if is_required("tech__main_functions") and not data.get("tech__main_functions"):
        main_functions = data.get("product__main_functions", "")
        if main_functions:
            data["tech__main_functions"] = f"系统主要功能包括：{main_functions}"

    if is_required("tech__features") and not data.get("tech__features"):
        tech_specs = data.get("product__tech_specs", "")
        if tech_specs:
            specs_text = tech_specs.replace("；", "，") if isinstance(tech_specs, str) else tech_specs
            data["tech__features"] = f"技术特点体现在：{specs_text}"

    if is_required("env__dev_lang") and data.get("env__language") and not data.get("env__dev_lang"):
        data["env__dev_lang"] = data.get("env__language")

    if is_required("env__os") and not data.get("env__os"):
        data["env__os"] = "Windows, Linux, macOS"

    if is_required("env__memory_req") and not data.get("env__memory_req"):
        data["env__memory_req"] = "2048MB"

    if is_required("env__dev_platform") and not data.get("env__dev_platform") and data.get("env__sw_dev_platform"):
        data["env__dev_platform"] = data.get("env__sw_dev_platform")

    if is_required("env__run_platform") and data.get("env__os") and not data.get("env__run_platform"):
        data["env__run_platform"] = data.get("env__os")

    return data
