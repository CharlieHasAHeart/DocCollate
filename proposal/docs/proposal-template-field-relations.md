## 1) 引言层：立项文档的“定义域”字段组（顺序 + 并列）

### A. 目的-范围-术语-依据链（顺序关系）

- 字段组：`purpose → scope → terms → references_list`
- 关系说明：
  1. `purpose` 先定义“为什么做”；
  2. `scope` 再界定“做什么/不做什么”；
  3. `terms` 用来统一口径，确保后续章节表述一致；
  4. `references_list` 为上述定义提供证据与来源（制度/标准/报告/评审材料）。

### B. 术语表内的并列关系（并列关系）

- 字段组：`terms[].term ∥ terms[].definition`
- 关系说明：每个术语项是“名词-解释”的一一对应，所有项彼此并列，共同组成统一口径。

### C. 参考资料表内的并列关系（并列关系）

- 字段组：`references_list[].title ∥ type ∥ date ∥ version ∥ note`
- 关系说明：同一条参考资料由多列属性并列描述；多条参考资料之间并列。

---

## 2) 项目背景层：从“问题”到“目标与衡量”的推导链（顺序 + 因果）

### D. 来源-现状-痛点-影响量化（顺序/因果关系）

- 字段组：`project_source → current_state → pain_points → impact_quantification`
- 关系说明：先交代立项来源，再描述现状，再抽取痛点，最后用量化影响证明“必须做/不做的代价”。

### E. 范围&目标的分解组（并列 + 约束关系）

- 字段组：`project_scope_objectives ∥ goals_smart ∥ north_star_metric`
- 关系说明：
  - `project_scope_objectives` 给出总体范围与目标集合；
  - `goals_smart` 把目标写成可执行、可验收的 SMART 表达；
  - `north_star_metric` 是所有目标的“总牵引指标”，用于在目标冲突时做取舍（约束/统摄关系）。

### F. 指标体系：基线-目标-测量方法（顺序/可验收关系）

- 字段组：`baseline_metrics → target_metrics → measurement_method`
- 关系说明：没有 `baseline_metrics` 就无法证明提升；`target_metrics` 必须以基线为参照；`measurement_method` 决定指标是否可审计、可复现。

### G. 客户/用户画像链（并列 + 输入到需求的关系）

- 字段组：`potential_customers ∥ personas ∥ user_journeys`
- 关系说明：
  - `potential_customers` 说明面向哪些对象；
  - `personas` 抽象典型角色；
  - `user_journeys` 描述角色的端到端流程；
    三者共同作为后续“场景、需求、测试范围”的输入。

### H. 约束-假设-依赖（并列 + 风险触发源关系）

- 字段组：`constraints ∥ assumptions ∥ dependencies`
- 关系说明：三者并列，但都是后续设计/计划/风险的“边界条件与不确定性来源”：
  - `constraints` 是硬边界（必须遵守）。模板中以 `constraints` 表格呈现（非文本占位符）。
  - `assumptions` 是成立前提（若不成立会影响计划/范围）；
  - `dependencies` 是外部交付/系统前置（延迟会影响关键路径）。

---

## 3) 方案与产品设计层：从“场景”到“MVP边界”再到“数据口径”的主链（顺序 + 分层）

### I. 场景-优先级（顺序关系）

- 字段组：`core_scenarios → scenario_prioritization`
- 关系说明：先列业务场景，再给排序/分级规则（否则后续 P0/P1 无依据）。

### J. 需求总览：功能 vs 非功能（并列关系）

- 字段组：`functional_requirements ∥ nonfunctional_requirements`
- 关系说明：两类需求并列，分别约束“做什么”与“做到什么程度”（性能/安全/可用性等）。

### K. MVP边界三件套（顺序/排他关系）

- 字段组：`mvp_features_p0 ∥ mvp_features_p1 ∥ mvp_exclusions`
- 关系说明：
  - P0/P1 是并列分层（优先级不同）；
  - `mvp_exclusions` 与 P0/P1 具有排他关系（明确不做，防止范围蔓延）；
  - 这组内容应由“场景优先级 + 需求总览 + 约束/依赖”推导出来。

### L. 功能描述承接MVP（细化关系）

- 字段组：`product_features`（对 `mvp_features_p0/p1` 的细化）
- 关系说明：`product_features` 是把MVP清单“解释成可实现的功能规格/模块描述”。

### M. 数据与报表口径三件套（顺序/定义关系）

- 字段组：`data_entities → metrics_definitions → report_list`
- 关系说明：先定义实体（数据从哪来、长什么样），再定义指标（如何算），最后才能列报表（呈现哪些指标）。

### N. 信息架构到页面清单（顺序关系）

- 字段组：`ia_sitemap → page_list`
- 关系说明：先有信息架构/导航树，才能落到页面级清单与范围确认。

### O. 路线图与退役计划（并列 + 约束未来范围）

- 字段组：`product_goals ∥ deprecation_plan`
- 关系说明：一个描述“新增演进目标”，一个描述“老能力/旧系统如何退出”，两者共同决定长期范围与迁移策略。

---

## 4) 技术方案层：从架构到运维到PoC的工程闭环（顺序 + 依赖）

### P. 架构三联（并列 + 决策约束）

- 字段组：`architecture ∥ system_context_diagram ∥ key_arch_decisions`
- 关系说明：总体架构与系统上下文并列描述“结构与边界”，`key_arch_decisions` 是对关键取舍给出不可逆约束（影响后续数据/集成/部署）。

### Q. 数据治理链（顺序关系）

- 字段组：`data_sources → data_pipeline → data_storage_strategy → data_retention_policy`
- 关系说明：数据从哪来决定管道怎么建；管道决定存储策略；存储策略必须落到保留与归档策略。

### R. 集成链（顺序 + 风险挂接）

- 字段组：`integration_systems → api_contracts → integration_risks`
- 关系说明：先列对接系统，再定义接口契约，最后识别对接风险（该风险应进入风险清单）。

### S. 安全合规链（并列 + 映射关系）

- 字段组：`authn_authz_model ∥ security_controls ∥ compliance_mapping`
- 关系说明：认证鉴权模型 + 控制措施是“怎么做安全”，`compliance_mapping` 是“把安全措施映射到合规条款/要求”的可审计证明。

### T. 性能容量链（顺序/验收关系）

- 字段组：`sla_targets → capacity_estimation → performance_test_plan`
- 关系说明：SLA目标决定容量估算；容量估算决定性能测试计划；性能测试计划用于证明SLA可达成。

---

## 5) 项目计划与交付层：从组织到资源到里程碑到质量与治理（顺序 + 依赖）

### U. 组织与资源（顺序/支撑关系）

- 字段组：`org_structure → resources[]`
- 关系说明：先明确组织与职责，再列资源明细（人员/软硬件）来支撑计划与交付。

### V. 里程碑五阶段表（并列结构 + 顺序推进）

- 字段组（每一阶段内部并列）：
  `milestone_0x_phase ∥ milestone_0x_tasks ∥ milestone_0x_time ∥ milestone_0x_deliverables`（x=01..05）
- 阶段间关系：01→02→03→04→05 为顺序推进（后阶段依赖前阶段交付物）。

### W. 质量保证三件套（顺序/退出标准依赖）

- 字段组：`qa_strategy → test_scope → exit_criteria`
- 关系说明：测试策略决定覆盖思路；覆盖范围定义测什么；退出标准用来“能否进入下一阶段/上线”。

### X. 项目治理三件套（并列 + 变更约束）

- 字段组：`governance_model ∥ comms_plan ∥ change_control`
- 关系说明：治理模型、沟通计划、变更控制并列构成项目运行机制，其中 `change_control` 直接约束范围/进度/成本变更。

---

## 6) 预算与收益层：从成本到收益到ROI（顺序 + 模型依赖）

### Y. 成本拆分表（并列关系）

- 字段组：`costs[].item ∥ costs[].amount ∥ costs[].note`
- 关系说明：每条成本项由名称、金额、备注并列描述；多条成本项并列汇总为总投入。

### Z. 收益三分法（并列关系）

- 字段组：`benefits_revenue ∥ benefits_cost_saving ∥ benefits_risk_avoidance`
- 关系说明：收入、降本、风险规避并列组成收益口径，后续ROI模型通常以此为输入。

### AA. ROI链（顺序/计算依赖）

- 字段组：`roi_model → payback_period → sensitivity_analysis`
- 关系说明：先给ROI模型（公式/假设），才能得回收期；敏感性分析用于检验关键假设变化时ROI是否仍成立。

---

## 7) 风险层：风险识别到监控预案（顺序 + 追溯）

### AB. 风险登记册字段（并列关系）

- 字段组：`risk_register[].id ∥ description ∥ probability ∥ impact ∥ level ∥ trigger ∥ mitigation`
- 关系说明：同一风险由多维字段并列描述；其中 `trigger` 与 `mitigation` 构成“触发-应对”的逻辑对子。

### AC. 风险闭环（顺序关系）

- 字段组：`risk_register → risk_monitoring_plan → contingency_plans`
- 关系说明：先列风险清单，再给监控机制，最后给预案（风险发生时怎么兜底）。

---

## 8) 上线与运营层：从发布到运维到培训再到迭代（顺序 + 并列）

### AD. 上线链（顺序关系）

- 字段组：`rollout_strategy → cutover_plan`
- 关系说明：先定灰度/试点策略，再给切换方案（切换是策略落地的一部分）。

### AE. 运维保障三件套（并列 + SLA约束）

- 字段组：`ops_model ∥ support_sla ∥ maintenance_plan`
- 关系说明：运维模式、支持SLA、维护计划并列构成运行保障体系，其中 `support_sla` 对运维资源与流程提出约束。

### AF. 培训赋能二件套（并列/交付物关系）

- 字段组：`training_plan ∥ enablement_assets`
- 关系说明：培训计划说明“怎么教”；赋能资产是“教什么/给什么材料”，两者共同支撑上线成功。

### AG. 运营与迭代闭环（顺序关系）

- 字段组：`ops_kpis → iteration_process`
- 关系说明：先定义运营KPI（怎么衡量运行效果），再定义持续迭代机制（如何基于KPI与反馈推动版本演进）。

---

## 9) 总结层：结论-决策请求-两周行动（顺序/决策闭环）

### AH. 决策闭环三件套（严格顺序关系）

- 字段组：`conclusion → decision_request → next_steps_2weeks`
- 关系说明：
  1. `conclusion` 给出是否建议立项的总判断；
  2. `decision_request` 明确需要管理层批准什么（预算/人力/权限/里程碑等）；
  3. `next_steps_2weeks` 把决策落地为可执行的近期行动清单（把“批了以后干什么”说清楚）。

---

# 10) 跨章节“可追溯关系”字段组（最容易写错但最重要）

这些不是模板里相邻字段，但在评审逻辑上必须能互相“对得上”，否则会被质疑。

### AI. 目标牵引链：目标 → 需求 → MVP → 里程碑 → 验收

- 字段组：`goals_smart/north_star_metric → functional_requirements → mvp_features_p0 → milestone_0x_deliverables → exit_criteria`
- 关系说明：目标必须能映射到需求；需求必须能落到 P0；P0 必须在里程碑交付物中体现；最终由退出标准验收。

### AJ. 场景牵引链：用户旅程/场景 → 页面/报表 → 测试范围

- 字段组：`user_journeys/core_scenarios → ia_sitemap/page_list + report_list → test_scope`
- 关系说明：场景/旅程决定需要哪些页面与报表；这些内容必须进入测试范围，否则“做出来没人用、测不到关键路径”。

### AK. 合规链：合规要求 → 安全映射 → 测试/上线前置

- 字段组：`regulatory_requirements/data_privacy_requirements/certification_plan → compliance_mapping → exit_criteria（或上线门禁）`
- 关系说明：合规要求需要被映射到具体安全控制；并最终体现为上线/阶段退出的门禁条件。

### AL. SLA链：SLA目标 → 容量估算/资源 → 成本 → 运维SLA

- 字段组：`sla_targets → capacity_estimation → resources[]/costs[] → support_sla`
- 关系说明：你承诺的SLA越高，容量与资源越大，成本越高；上线后的支持SLA要与前面的SLA目标一致。

### AM. 假设/依赖到风险闭环：假设/依赖 → 集成风险/技术风险 → 风险登记册 → 预案

- 字段组：`assumptions/dependencies → integration_risks/technical_risks → risk_register → contingency_plans`
- 关系说明：假设与依赖不成立时应转化为风险项，进入登记册，并配置监控与预案。

---
