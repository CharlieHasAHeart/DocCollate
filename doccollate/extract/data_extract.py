from __future__ import annotations

import re


def parse_markdown_tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    tables = []
    lines = text.splitlines()
    idx = 0
    while idx < len(lines):
        if "|" not in lines[idx]:
            idx += 1
            continue
        header = [col.strip() for col in lines[idx].split("|") if col.strip()]
        if idx + 1 >= len(lines):
            break
        separator = lines[idx + 1]
        if set(separator.replace("|", "").strip()) <= {"-", ":"}:
            idx += 2
            rows = []
            while idx < len(lines) and "|" in lines[idx]:
                row = [col.strip() for col in lines[idx].split("|") if col.strip()]
                if row:
                    rows.append(row)
                idx += 1
            tables.append((header, rows))
        else:
            idx += 1
    return tables


def extract_app_from_text(text: str) -> dict:
    data: dict[str, object] = {}
    short_name_patterns = [
        r"软件简称[:：]\s*(.+)",
        r"系统简称[:：]\s*(.+)",
    ]
    for pattern in short_name_patterns:
        match = re.search(pattern, text)
        if match:
            data["app__short_name"] = match.group(1).strip()
            break

    category_patterns = [
        r"所属类别[:：]\s*(.+)",
        r"软件类别[:：]\s*(.+)",
    ]
    for pattern in category_patterns:
        match = re.search(pattern, text)
        if match:
            data["app__product_type"] = match.group(1).strip()
            break

    match = re.search(r"应用领域[:：]\s*(.+)", text)
    if match:
        data["product__app_domain"] = match.group(1).strip()
    return data


def extract_func_list_from_text(text: str) -> dict:
    data: dict[str, object] = {}
    match = re.search(r"功能模块[:：]\s*(.+)", text)
    if match:
        data["product__func_list"] = match.group(1).strip()
    return data


def extract_env_from_tables(text: str) -> dict:
    data: dict[str, object] = {}
    for headers, rows in parse_markdown_tables(text):
        for row in rows:
            if len(row) < 2:
                continue
            category = row[0]
            value = row[1]
            if "开发硬件环境" in category:
                data["env__hw_dev_platform"] = value
                data["tech__hardware_dev"] = value
            elif "开发该软件的操作系统" in category or "开发操作系统" in category:
                data["tech__os_dev"] = value
            elif "编程语言" in category:
                data["env__language"] = value
                data["tech__language"] = value
            elif "开发环境" in category or "开发工具" in category:
                data["env__sw_dev_platform"] = value
                data["tech__dev_tools"] = value
            elif "运行硬件环境" in category:
                data["tech__hardware_run"] = value
                data["env__server_config"] = value
                data["env__client_config"] = value
            elif "运行平台" in category or "运行操作系统" in category:
                data["env__server_os"] = value
                data["env__client_os"] = value
                data["tech__os_run"] = value
            elif "运行支撑" in category or "支持软件" in category:
                data["env__server_soft"] = value
                data["env__client_soft"] = value
                data["tech__run_support"] = value
    return data


def extract_rule_data(text: str) -> dict:
    data: dict[str, object] = {}
    data.update(extract_app_from_text(text))
    data.update(extract_func_list_from_text(text))
    data.update(extract_env_from_tables(text))
    return data
