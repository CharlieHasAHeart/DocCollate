# DocCollate 数据字段生成逻辑

本文档描述 `data` 字典的字段来源与生成逻辑，适用于三类文件（立项建议书/测试表/软著申请表）。

## 生成流程总览

1. `summarize_spec()`：对说明书生成摘要（供检索不足时兜底）。
2. `extract_func_items()` + `extract_fields_by_prompt()`：BM25 检索证据后交给 LLM 生成字段与功能清单。
3. `sanitize_data()`：清洗 HTML 换行与列表字段。
4. `normalize_assessment_data()`：评估表字段默认值、日期与部分环境字段归一化。
5. `derive_fields()`：生成技术字段、默认值与文本前缀拼接。
6. `apply_app_metadata()`：用交互式输入覆盖软件名称/版本与申请人类型。

## 交互式输入（CLI）

这些字段不从说明书匹配，直接来自交互输入：

- `app__name`：软件名称（命令行交互输入）
- `app__version`：软件版本号（命令行交互输入）
- `applicant__type`：申请人类型（holder/agent，交互输入）

> 每次运行只问一次，三类文件共享。

## BM25 检索 + LLM 生成（extract_fields_by_prompt）

说明书字段统一流程：

1. 使用 BM25 在说明书分段中检索证据。
2. 将证据 + 说明书摘要交给 LLM 生成字段内容。
3. 若检索证据长度不足 400 字符，则以摘要 + 说明书片段为主进行生成，避免大量“待确认”。

从说明书内容中由 LLM 生成：

- `app__product_type`
- `app__category_assess`
- `product__service_object`
- `product__main_functions`
- `product__tech_specs`
- `product__app_domain`
- `env__dev_platform`
- `env__run_platform`
- `env__hw_dev_platform`
- `env__sw_dev_platform`
- `env__memory_req`
- `env__hardware_model`
- `env__server_config`
- `env__client_config`
- `env__server_os`
- `env__client_os`
- `env__os`
- `env__soft_scale`
- `env__language`
- `env__database`
- `env__os_version`
- `env__server_soft`
- `env__client_soft`

## 功能清单（LLM）

- `product__func_list`：LLM 从模块证据中生成列表
  - 列表项包含 `一级功能`、`功能描述`
  - 若证据不足，改用说明书摘要生成
  - 若描述缺失，会在 `derive_fields()` 中补齐

## 评估表字段归一化（normalize_assessment_data）

默认值/格式化：

- `assess__support_floppy` / `assess__support_sound` / `assess__support_cdrom` / `assess__support_gpu` / `assess__support_other`：默认 `False`
- `assess__is_self_dev` / `assess__has_docs` / `assess__has_source`：默认 `True`
- `assess__workload`：若有数字则格式化为 `X人*Y月`，否则 `3人*3月`
- `env__memory_req`：若能提取数字则格式化为 `NNMB`
- `env__soft_scale`：默认 `中`
- `env__database`：默认 `PostgreSQL 13`
- `env__os_version`：默认 `Ubuntu 22.04 LTS`
- `app__product_type_text`：由 `app__product_type` 规范化得到
- `app__category_assess`：分类号标准化

日期（来自 `pyproject.toml` 的偏移配置）：

- `copyright__completion_date`：当前日期往前 `assess_completion_days_ago` 天，回退到工作日
- `assess__completion_date`：与 `copyright__completion_date` 相同
- `assess__dev_date`：从 `assess__completion_date` 往前 `assess_dev_months_ago` 个月，回退到工作日

随机默认值（说明书未提供时作为兜底）：

- `env__server_model` / `env__server_config`
- `env__client_model` / `env__client_config`
- `env__server_os` / `env__client_os`

## 派生字段与默认值（derive_fields）

默认值：

- `tech__source_lines`：`"15000"`
- `app__short_name`：强制为 `"无"`
- `app__classification_code`：强制为空字符串
- `env__dev_lang`：若为空则等于 `env__language`
- `env__os`：默认 `"Windows, Linux, macOS"`
- `env__memory_req`：默认 `"2048MB"`
- `env__dev_platform`：若为空则用 `env__sw_dev_platform`
- `env__run_platform`：若为空则用 `env__os`

从已有字段拼接生成：

- `product__main_functions`：若为空则从 `product__func_list` 汇总
- `tech__main_functions`：`"系统主要功能包括：{product__main_functions}"`
- `tech__features`：`"技术特点体现在：{product__tech_specs}"`
- `tech__dev_purpose`：`"开发目的在于服务{product__service_object}，解决其业务需求。"`
- `tech__hardware_dev`：`"开发硬件环境：{env__hw_dev_platform}"`
- `tech__dev_tools`：`"开发工具与平台：{env__sw_dev_platform}"`
- `tech__os_dev`：优先 `env__os_version`，其次 `env__os`，再回退 `env__server_os/ env__client_os`
- `tech__os_run`：服务器端/客户端拼接
- `tech__run_support`：服务器端/客户端拼接
- `tech__hardware_run`：服务器端/客户端硬件拼接
- `tech__language`：等于 `env__language`

## 软著模板字段（fill_form）

软著模板会消耗这些字段（空则留空）：

- 软件基础字段：`app__name`、`app__version`、`app__short_name`、`app__classification_code`
- 技术字段：`tech__hardware_dev`、`tech__hardware_run`、`tech__os_dev`、`tech__os_run`、`tech__dev_tools`、`tech__run_support`、`tech__language`、`tech__dev_purpose`、`tech__main_functions`、`tech__features`、`tech__source_lines`
- 软著状态字段：`copyright__status_published`、`copyright__publish_date`、`copyright__publish_location`
- 开发方式字段：`copyright__development_method`
- 权利取得字段：`rights__acquire_method`、`rights__scope`、`rights__partial_rights`、`rights__succession_details`
- 修改信息字段：`modification_details`
- 签章日期：`signature__date`
- 申请人类型：`applicant__type`

## 评估表/测试表字段

评估表与测试表使用的字段见 `doccollate/core/constants.py` 与 `doccollate/render/renderers.py`：

- `product__service_object`、`product__main_functions`、`product__tech_specs`
- `app__product_type_text`、`app__category_assess`
- `env__memory_req`、`env__hardware_model`、`env__os`、`env__language`、`env__database`、`env__soft_scale`、`env__os_version`
- `env__hw_dev_platform`、`env__sw_dev_platform`
- `assess__workload`、`assess__dev_date`、`assess__completion_date`
- 勾选项：`assess__support_*`、`assess__is_self_dev`、`assess__has_docs`、`assess__has_source`

```json
{
  "assess__support_floppy": false,
  "assess__support_sound": false,
  "assess__support_cdrom": false,
  "assess__support_gpu": false,
  "assess__support_other": false
}
```

## 立项建议书字段（proposal）

立项建议书使用单独的 `manual_inputs` 和 LLM 输出，不依赖 `data`。其中里程碑日期由：

- `manual_inputs.schedule.start_date = assess__dev_date`
- `manual_inputs.schedule.end_date = assess__completion_date`

若需新增字段映射或规则，请在 `extract/` 与 `derive_fields()` 中补齐。
