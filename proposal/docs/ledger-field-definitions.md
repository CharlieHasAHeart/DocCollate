# 台账模型字段说明（硬性标准）

本台账模型仅保存“硬性标准/约束”，用于统一立项建议书的刚性口径。
字段路径用于定位 JSON 中的位置，列表字段用 `[]` 表示元素。
“对应正文占位符/表格”用于说明该字段主要服务的模板位置（可一对多）。

## delivery_window

| 字段路径 | 类型 | 含义 | 对应正文占位符/表格 |
| --- | --- | --- | --- |
| `delivery_window.start` | `str` | 交付窗口开始日期（YYYY-MM-DD） | 表格：`milestones` |
| `delivery_window.end` | `str` | 交付窗口结束日期（YYYY-MM-DD） | 表格：`milestones` |

## poc_window

| 字段路径 | 类型 | 含义 | 对应正文占位符/表格 |
| --- | --- | --- | --- |
| `poc_window.start` | `str` | PoC 窗口开始日期（YYYY-MM-DD） | `{{ technical_feasibility_and_poc_plan }}`, `{{ product_roadmap }}` |
| `poc_window.end` | `str` | PoC 窗口结束日期（YYYY-MM-DD） | `{{ technical_feasibility_and_poc_plan }}`, `{{ product_roadmap }}` |

## key_timepoints（关键时间点）

> 关键时间点与里程表阶段的联动关系遵循 `时间逻辑.md` 描述，且全部时间点必须落在 `delivery_window` 内。

| 字段路径 | 类型 | 含义 | 联动里程表阶段/约束 |
| --- | --- | --- | --- |
| `key_timepoints.kickoff` | `str` | 项目启动 / 交付窗口期开始（YYYY-MM-DD） | 等于 `delivery_window.start`，同时对齐里程表第1阶段起点 |
| `key_timepoints.delivery_window_start` | `str` | 交付窗口期开始（YYYY-MM-DD） | 等于 `delivery_window.start` |
| `key_timepoints.interface_freeze` | `str` | 环境与接口口径冻结点 | 对齐里程表第1阶段终点（退出条件） |
| `key_timepoints.poc_start` | `str` | POC 启动点 | 对齐里程表第2阶段起点，等于 `poc_window.start` |
| `key_timepoints.poc_end` | `str` | POC 验收/结论点 | 对齐里程表第2阶段终点，等于 `poc_window.end` |
| `key_timepoints.full_function_complete` | `str` | 全功能开发完成点 | 必须落在里程表第3阶段时间段内 |
| `key_timepoints.integration_complete` | `str` | 三方接口集成完成点 | 对齐里程表第3阶段终点（退出条件） |
| `key_timepoints.uat_start` | `str` | UAT 开始点 | 对齐里程表第4阶段起点 |
| `key_timepoints.uat_pass` | `str` | UAT 通过点 | 对齐里程表第4阶段终点（退出条件） |
| `key_timepoints.launch_window_start` | `str` | 上线窗口开始点 | 对齐里程表第5阶段起点 |
| `key_timepoints.stabilization_window.start` | `str` | 稳定运行观察期起点 | 落在里程表第5阶段时间段内 |
| `key_timepoints.stabilization_window.end` | `str` | 稳定运行观察期终点 | 落在里程表第5阶段时间段内 |
| `key_timepoints.handover_complete` | `str` | 移交完成点 | 对齐里程表第5阶段终点（退出条件） |
| `key_timepoints.delivery_window_end` | `str` | 交付窗口期截止点 | 等于 `delivery_window.end`，同时对齐里程表第5阶段终点 |

## scope_boundary

| 字段路径 | 类型 | 含义 | 对应正文占位符/表格 |
| --- | --- | --- | --- |
| `scope_boundary.inclusions[]` | `str` | 必须纳入的范围项 | `{{ scope }}`, `{{ project_scope_and_objectives }}` |
| `scope_boundary.exclusions[]` | `str` | 明确排除的范围项 | `{{ scope }}`, `{{ project_scope_and_objectives }}` |

## acceptance_criteria

| 字段路径 | 类型 | 含义 | 对应正文占位符/表格 |
| --- | --- | --- | --- |
| `acceptance_criteria.acceptance_definition` | `str` | 验收口径定义 | `{{ testing_and_quality_plan }}`, `{{ rollout_and_pilot_strategy }}` |
| `acceptance_criteria.exit_criteria` | `str` | 退出/验收标准 | `{{ testing_and_quality_plan }}`, `{{ rollout_and_pilot_strategy }}` |

## performance_capacity

| 字段路径 | 类型 | 含义 | 对应正文占位符/表格 |
| --- | --- | --- | --- |
| `performance_capacity.response_time` | `str` | 响应时间硬指标 | `{{ performance_capacity_sla }}` |
| `performance_capacity.user_concurrency` | `str` | 并发用户指标 | `{{ performance_capacity_sla }}` |
| `performance_capacity.device_connections` | `str` | 设备连接数指标 | `{{ performance_capacity_sla }}` |
| `performance_capacity.api_qps` | `str` | API QPS/吞吐指标 | `{{ performance_capacity_sla }}` |
| `performance_capacity.capacity_notes` | `str` | 容量口径补充说明 | `{{ performance_capacity_sla }}` |

## sla_support

| 字段路径 | 类型 | 含义 | 对应正文占位符/表格 |
| --- | --- | --- | --- |
| `sla_support.availability_target` | `str` | 可用性目标（硬性） | `{{ performance_capacity_sla }}` |
| `sla_support.rto_target` | `str` | RTO 目标（硬性） | `{{ operations_model_and_support_sla }}` |
| `sla_support.response_target` | `str` | 故障响应时效（硬性） | `{{ operations_model_and_support_sla }}` |
| `sla_support.support_window` | `str` | 支持窗口/到场承诺 | `{{ operations_model_and_support_sla }}` |

## compliance_requirements

| 字段路径 | 类型 | 含义 | 对应正文占位符/表格 |
| --- | --- | --- | --- |
| `compliance_requirements.data_residency` | `str` | 数据驻留/出境限制 | `{{ compliance_requirements }}`, `{{ data_architecture_and_governance }}` |
| `compliance_requirements.regulatory_requirements` | `str` | 法规/合规要求 | `{{ compliance_requirements }}` |
| `compliance_requirements.security_controls` | `str` | 必要安全控制 | `{{ security_access_and_audit }}` |
| `compliance_requirements.retention.business_data` | `str` | 业务数据留存 | `{{ data_architecture_and_governance }}` |
| `compliance_requirements.retention.audit_log` | `str` | 审计日志留存 | `{{ data_architecture_and_governance }}` |
| `compliance_requirements.retention.ops_log` | `str` | 运维日志留存 | `{{ data_architecture_and_governance }}` |
| `compliance_requirements.retention.device_raw` | `str` | 设备原始数据留存 | `{{ data_architecture_and_governance }}` |
| `compliance_requirements.retention.blockchain_data` | `str` | 区块链/链上数据留存 | `{{ data_architecture_and_governance }}` |
| `compliance_requirements.retention.notes` | `str` | 留存口径补充说明 | `{{ data_architecture_and_governance }}` |

## budget_resources

| 字段路径 | 类型 | 含义 | 对应正文占位符/表格 |
| --- | --- | --- | --- |
| `budget_resources.budget_total` | `str` | 总预算上限 | `{{ cost_estimate_and_budget }}` |
| `budget_resources.resource_constraints` | `str` | 资源/人力/设备上限约束 | `{{ cost_estimate_and_budget }}`, `{{ team_structure_and_responsibilities }}` |

## tables

> 表格为台账硬性口径的结构化输出，必须补齐最少行数。

### tables.terms（术语表，≥4行）

| 字段路径 | 类型 | 含义 | 对应正文占位符/表格 |
| --- | --- | --- | --- |
| `tables.terms[].term` | `str` | 术语 | 表格：`terms` |
| `tables.terms[].definition` | `str` | 定义 | 表格：`terms` |

### tables.resources（资源成本表，≥2行；需覆盖软件/硬件/人力三类）

| 字段路径 | 类型 | 含义 | 对应正文占位符/表格 |
| --- | --- | --- | --- |
| `tables.resources[].name` | `str` | 资源名称 | 表格：`resources` |
| `tables.resources[].level` | `str` | 等级/规格等级 | 表格：`resources` |
| `tables.resources[].spec` | `str` | 规格/配置 | 表格：`resources` |
| `tables.resources[].source` | `str` | 来源/采购方式 | 表格：`resources` |
| `tables.resources[].cost` | `str` | 成本 | 表格：`resources` |

### tables.milestones（里程碑，固定5行）

| 字段路径 | 类型 | 含义 | 对应正文占位符/表格 |
| --- | --- | --- | --- |
| `tables.milestones[].phase` | `str` | 阶段名称 | 表格：`milestones` |
| `tables.milestones[].tasks` | `str` | 关键任务 | 表格：`milestones` |
| `tables.milestones[].start_date` | `str` | 开始日期 | 表格：`milestones` |
| `tables.milestones[].end_date` | `str` | 结束日期 | 表格：`milestones` |
| `tables.milestones[].deliverables` | `str` | 交付物 | 表格：`milestones` |

### tables.references_list（引用清单，≥1行）

| 字段路径 | 类型 | 含义 | 对应正文占位符/表格 |
| --- | --- | --- | --- |
| `tables.references_list[].title` | `str` | 标题 | 表格：`references_list` |
| `tables.references_list[].type` | `str` | 类型 | 表格：`references_list` |
| `tables.references_list[].date` | `str` | 日期 | 表格：`references_list` |
| `tables.references_list[].version` | `str` | 版本 | 表格：`references_list` |
| `tables.references_list[].note` | `str` | 备注 | 表格：`references_list` |

### tables.risk_register（风险登记，≥3行）

| 字段路径 | 类型 | 含义 | 对应正文占位符/表格 |
| --- | --- | --- | --- |
| `tables.risk_register[].id` | `str` | 风险编号 | 表格：`risk_register` |
| `tables.risk_register[].description` | `str` | 风险描述 | 表格：`risk_register` |
| `tables.risk_register[].probability` | `str` | 发生概率 | 表格：`risk_register` |
| `tables.risk_register[].impact` | `str` | 影响 | 表格：`risk_register` |
| `tables.risk_register[].level` | `str` | 风险等级 | 表格：`risk_register` |
| `tables.risk_register[].trigger` | `str` | 触发条件 | 表格：`risk_register` |
| `tables.risk_register[].mitigation` | `str` | 缓解措施 | 表格：`risk_register` |
